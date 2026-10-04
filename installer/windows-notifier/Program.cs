using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Net;
using System.Security;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Web.Script.Serialization;
using Windows.Data.Xml.Dom;
using Windows.UI.Notifications;

namespace Lontrium.Notifier
{
    internal static class Program
    {
        private const string AppId = "RafaelCaires.LontriumControl";
        private const string Endpoint = "http://127.0.0.1:8080/api/windows-events";
        private const string ConfigEndpoint = "http://127.0.0.1:8080/api/config";
        private const string ActionEndpoint = "http://127.0.0.1:8080/api/windows-events/action";
        private const string BrowserUrl = "http://127.0.0.1:7080/?autoconnect=true";
        private static readonly HashSet<string> AllowedStores = new HashSet<string>(StringComparer.Ordinal)
        {
            "epic", "gog", "steam", "prime", "ubisoft", "unity", "fab",
            "gamerpower", "aliexpress", "shopee"
        };

        [STAThread]
        private static int Main(string[] args)
        {
            if (args.Length >= 1 && args[0] == "--scheduled")
            {
                string action = args.Length == 2 && args[1] == "start" ? "start" : "scheduled";
                return RunLauncher(action, true);
            }
            if (args.Length == 1 && args[0] == "--open")
            {
                StartLontrium();
                return 0;
            }
            if (args.Length == 2 && args[0] == "--toast-action")
            {
                HandleToastAction(args[1]);
                return 0;
            }
            if (args.Length == 1 && args[0] == "--launcher-failure")
            {
                Show(new ManualEvent { id = Guid.NewGuid().ToString("N"), kind = "launcher_failure", store = "system" });
                return 0;
            }
            if (args.Length == 4 && args[0] == "--notify"
                && Guid.TryParseExact(args[3], "N", out _))
            {
                Show(new ManualEvent { kind = args[1], store = args[2], id = args[3] });
                return 0;
            }
            using (var mutex = new Mutex(true, @"Local\LontriumControlNotifier", out bool ownsMutex))
            {
                if (!ownsMutex) return 0;
                Poll();
            }
            return 0;
        }

        private static void Poll()
        {
            var seen = LoadSeen();
            var unavailableSince = DateTime.UtcNow;
            string scheduleSignature = null;
            while (true)
            {
                EventResponse response = Fetch();
                if (response != null)
                {
                    unavailableSince = DateTime.UtcNow;
                    foreach (ManualEvent item in response.events ?? new ManualEvent[0])
                    {
                        if (!IsAllowed(item, response.enabled) || seen.Contains(item.id)) continue;
                        if (item.kind == "stop_all")
                        {
                            Remember(seen, item.id);
                            RunLauncher("stop", false);
                            return;
                        }
                        if (Show(item)) Remember(seen, item.id);
                    }
                }
                else if (DateTime.UtcNow - unavailableSince > TimeSpan.FromMinutes(2)) return;

                string currentSchedule = FetchScheduleSignature();
                if (currentSchedule != null)
                {
                    if (scheduleSignature != null && scheduleSignature != currentSchedule)
                        RunLauncher("sync-schedule", false);
                    scheduleSignature = currentSchedule;
                }
                Thread.Sleep(TimeSpan.FromSeconds(3));
            }
        }

        private static EventResponse Fetch()
        {
            try { return GetJson<EventResponse>(Endpoint); }
            catch { return null; }
        }

        private static string FetchScheduleSignature()
        {
            try
            {
                var config = GetJson<ConfigResponse>(ConfigEndpoint);
                if (config?.values == null) return null;
                return string.Join("|", config.values.WINDOWS_ECONOMY_SCHEDULE,
                    config.values.RUN_ON_STARTUP, config.values.WINDOWS_WAKE_ON_AC,
                    config.values.SCHEDULER_FIXED_TIMES ?? "",
                    string.Join(",", config.values.STORES ?? new string[0]));
            }
            catch { return null; }
        }

        private static T GetJson<T>(string endpoint)
        {
            var request = (HttpWebRequest)WebRequest.Create(endpoint);
            request.Proxy = null;
            request.Timeout = 2500;
            request.ReadWriteTimeout = 2500;
            request.UserAgent = "Lontrium-Notifier/1";
            using (var response = (HttpWebResponse)request.GetResponse())
            using (var stream = response.GetResponseStream())
            using (var reader = new StreamReader(stream, Encoding.UTF8))
            {
                if (response.StatusCode != HttpStatusCode.OK) return default(T);
                return new JavaScriptSerializer().Deserialize<T>(reader.ReadToEnd());
            }
        }

        private static bool IsAllowed(ManualEvent item, bool notificationsEnabled)
        {
            if (item == null || !Guid.TryParseExact(item.id, "N", out _)) return false;
            if (item.kind == "stop_all") return item.store == "system";
            if (item.kind == "launcher_failure") return item.store == "system";
            return notificationsEnabled
                && (((item.kind == "captcha" || item.kind == "failure" || item.kind == "timeout")
                    && AllowedStores.Contains(item.store ?? ""))
                    || (item.kind == "login_required" && item.store == "aliexpress")
                    || (item.kind == "run_timeout" && item.store == "system"));
        }

        private static bool Show(ManualEvent item)
        {
            try
            {
                string language = CultureInfo.CurrentUICulture.TwoLetterISOLanguageName;
                string title;
                string body;
                bool actionable = false;
                string storeName = item.store == "system" ? "Lontrium" : StoreName(item.store);

                if (item.kind == "captcha")
                {
                    title = language == "pt" ? "Lontrium — ação necessária" : language == "es" ? "Lontrium — acción necesaria" : "Lontrium — action required";
                    body = language == "pt" ? $"A {storeName} está aguardando a resolução de um CAPTCHA." : language == "es" ? $"{storeName} está esperando que resuelvas un CAPTCHA." : $"{storeName} is waiting for you to solve a CAPTCHA.";
                    actionable = true;
                }
                else if (item.kind == "login_required")
                {
                    title = language == "pt" ? "Lontrium — login necessário" : language == "es" ? "Lontrium — inicio de sesión necesario" : "Lontrium — login required";
                    body = language == "pt" ? "A sessão do AliExpress expirou. Entre novamente para proteger sua sequência." : language == "es" ? "La sesión de AliExpress caducó. Inicia sesión de nuevo para proteger tu racha." : "Your AliExpress session expired. Sign in again to protect your streak.";
                    actionable = true;
                }
                else if (item.kind == "timeout")
                {
                    title = language == "pt" ? "Lontrium — tempo limite excedido" : language == "es" ? "Lontrium — tiempo de espera agotado" : "Lontrium — store timed out";
                    body = language == "pt" ? $"A {storeName} demorou demais. Ela continuará pendente e será tentada novamente." : language == "es" ? $"{storeName} tardó demasiado. Seguirá pendiente y se volverá a intentar." : $"{storeName} took too long. It remains pending and will be retried.";
                }
                else if (item.kind == "run_timeout")
                {
                    title = language == "pt" ? "Lontrium — execução interrompida" : language == "es" ? "Lontrium — ejecución interrumpida" : "Lontrium — run interrupted";
                    body = language == "pt" ? "A rodada excedeu o limite de tempo. As lojas incompletas serão tentadas novamente." : language == "es" ? "La ejecución excedió el límite de tiempo. Las tiendas incompletas se volverán a intentar." : "The run exceeded its time limit. Incomplete stores will be retried.";
                }
                else if (item.kind == "launcher_failure")
                {
                    title = language == "pt" ? "Lontrium — não foi possível iniciar" : language == "es" ? "Lontrium — no se pudo iniciar" : "Lontrium — could not start";
                    body = language == "pt" ? "A execução automática falhou antes de concluir. Abra o Lontrium para verificar." : language == "es" ? "La ejecución automática falló antes de finalizar. Abre Lontrium para comprobarlo." : "The automatic run failed before completion. Open Lontrium to investigate.";
                }
                else
                {
                    title = language == "pt" ? "Lontrium — falha na execução" : language == "es" ? "Lontrium — fallo de ejecución" : "Lontrium — run failed";
                    body = language == "pt" ? $"A execução da {storeName} falhou. Ela continuará pendente e será tentada novamente." : language == "es" ? $"La ejecución de {storeName} falló. Seguirá pendiente y se volverá a intentar." : $"{storeName} failed. It remains pending and will be retried.";
                }

                string openButton = language == "pt" || language == "es" ? "Abrir navegador" : "Open browser";
                string skipButton = language == "pt" ? "Pular agora" : language == "es" ? "Omitir ahora" : "Skip now";
                string image = new Uri(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "Lontrium.png")).AbsoluteUri;
                string openAction = "lontrium-action://open/" + item.id;
                string skipAction = "lontrium-action://skip/" + item.id;
                string xml = actionable ? "<toast launch=\"" + openAction + "\">" : "<toast>";
                xml += "<visual><binding template=\"ToastGeneric\"><text>" + Escape(title)
                    + "</text><text>" + Escape(body) + "</text><image placement=\"appLogoOverride\" hint-crop=\"circle\" src=\""
                    + Escape(image) + "\"/></binding></visual>";
                if (actionable)
                {
                    xml += "<actions><action content=\"" + Escape(openButton) + "\" arguments=\"" + openAction
                        + "\" activationType=\"protocol\"/><action content=\"" + Escape(skipButton) + "\" arguments=\""
                        + skipAction + "\" activationType=\"protocol\"/></actions>";
                }
                xml += "</toast>";
                var document = new XmlDocument();
                document.LoadXml(xml);
                var toast = new ToastNotification(document)
                {
                    Tag = Truncate(item.store ?? "system", 16),
                    Group = Truncate(item.kind ?? "event", 16),
                };
                ToastNotificationManager.CreateToastNotifier(AppId).Show(toast);
                return true;
            }
            catch { return false; }
        }

        private static void HandleToastAction(string value)
        {
            try
            {
                if (!Uri.TryCreate(value, UriKind.Absolute, out Uri uri) || uri.Scheme != "lontrium-action") return;
                string action = uri.Host;
                string id = uri.AbsolutePath.Trim('/');
                if (!Guid.TryParseExact(id, "N", out _)) return;
                if (action == "open")
                {
                    if (DashboardAvailable()) Process.Start(new ProcessStartInfo { FileName = BrowserUrl, UseShellExecute = true });
                    else StartLontrium();
                }
                else if (action == "skip") PostDecision(id);
            }
            catch { }
        }

        private static void PostDecision(string id)
        {
            try
            {
                string html;
                var page = (HttpWebRequest)WebRequest.Create("http://127.0.0.1:8080/");
                page.Proxy = null;
                page.Timeout = 2500;
                using (var response = page.GetResponse())
                using (var reader = new StreamReader(response.GetResponseStream(), Encoding.UTF8)) html = reader.ReadToEnd();
                var match = Regex.Match(html, "<meta\\s+name=\"fgc-token\"\\s+content=\"([^\"]+)\"", RegexOptions.IgnoreCase);
                if (!match.Success) return;
                byte[] body = Encoding.UTF8.GetBytes("{\"id\":\"" + id + "\",\"action\":\"skip\"}");
                var request = (HttpWebRequest)WebRequest.Create(ActionEndpoint);
                request.Method = "POST";
                request.Proxy = null;
                request.Timeout = 2500;
                request.ContentType = "application/json";
                request.Headers["X-FGC-Token"] = WebUtility.HtmlDecode(match.Groups[1].Value);
                request.ContentLength = body.Length;
                using (var stream = request.GetRequestStream()) stream.Write(body, 0, body.Length);
                using (request.GetResponse()) { }
            }
            catch { }
        }

        private static void StartLontrium()
        {
            if (DashboardAvailable())
            {
                try { Process.Start(new ProcessStartInfo { FileName = "http://127.0.0.1:8080/", UseShellExecute = true }); }
                catch { }
                return;
            }
            RunLauncher("start", false);
        }

        private static bool DashboardAvailable()
        {
            try
            {
                var request = (HttpWebRequest)WebRequest.Create("http://127.0.0.1:8080/api/status");
                request.Proxy = null;
                request.Timeout = 1000;
                using (var response = (HttpWebResponse)request.GetResponse()) return response.StatusCode == HttpStatusCode.OK;
            }
            catch { return false; }
        }

        private static int RunLauncher(string action, bool wait)
        {
            try
            {
                string launcher = FindLauncher();
                if (!File.Exists(launcher)) return 2;
                var process = Process.Start(new ProcessStartInfo
                {
                    FileName = "powershell.exe",
                    Arguments = "-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File \"" + launcher + "\" -Action " + action + " -Language auto",
                    WorkingDirectory = Path.GetDirectoryName(launcher),
                    UseShellExecute = false,
                    CreateNoWindow = true,
                });
                if (!wait || process == null) return process == null ? 3 : 0;
                process.WaitForExit();
                return process.ExitCode;
            }
            catch { return 1; }
        }

        private static string FindLauncher()
        {
            string installed = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "Start-ClaimerControl.ps1");
            if (File.Exists(installed)) return installed;
            return Path.GetFullPath(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "..", "..", "..", "..", "Start-ClaimerControl.ps1"));
        }

        private static string StoreName(string store)
        {
            switch (store)
            {
                case "epic": return "Epic Games";
                case "gog": return "GOG";
                case "aliexpress": return "AliExpress";
                case "shopee": return "Shopee";
                case "ubisoft": return "Ubisoft";
                case "prime": return "Prime Gaming";
                case "gamerpower": return "GamerPower";
                default: return string.IsNullOrEmpty(store) ? "Lontrium" : char.ToUpperInvariant(store[0]) + store.Substring(1);
            }
        }

        private static string Escape(string value) => SecurityElement.Escape(value) ?? "";
        private static string Truncate(string value, int length) => value.Substring(0, Math.Min(length, value.Length));
        private static string SeenPath => Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Lontrium Control", "notifier-events.txt");

        private static HashSet<string> LoadSeen()
        {
            try { return new HashSet<string>(File.ReadAllLines(SeenPath), StringComparer.Ordinal); }
            catch { return new HashSet<string>(StringComparer.Ordinal); }
        }

        private static void Remember(HashSet<string> seen, string id)
        {
            seen.Add(id);
            try
            {
                Directory.CreateDirectory(Path.GetDirectoryName(SeenPath));
                File.AppendAllLines(SeenPath, new[] { id });
            }
            catch { }
        }

        private sealed class EventResponse { public bool enabled { get; set; } public ManualEvent[] events { get; set; } }
        private sealed class ManualEvent { public string id { get; set; } public string kind { get; set; } public string store { get; set; } }
        private sealed class ConfigResponse { public ScheduleValues values { get; set; } }
        private sealed class ScheduleValues
        {
            public bool WINDOWS_ECONOMY_SCHEDULE { get; set; }
            public bool RUN_ON_STARTUP { get; set; }
            public bool WINDOWS_WAKE_ON_AC { get; set; }
            public string SCHEDULER_FIXED_TIMES { get; set; }
            public string[] STORES { get; set; }
        }
    }
}
