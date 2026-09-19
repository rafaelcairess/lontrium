using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Net;
using System.Security;
using System.Text;
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
        private const string BrowserUrl = "http://127.0.0.1:7080/?autoconnect=true";
        private static readonly HashSet<string> AllowedStores = new HashSet<string>(StringComparer.Ordinal)
        {
            "epic", "gog", "steam", "prime", "ubisoft", "unity", "fab",
            "gamerpower", "aliexpress", "shopee"
        };

        [STAThread]
        private static void Main()
        {
            using (var mutex = new Mutex(true, @"Local\LontriumControlNotifier", out bool ownsMutex))
            {
                if (!ownsMutex) return;
                Poll();
            }
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
                    if (response.events != null)
                    {
                        foreach (ManualEvent item in response.events)
                        {
                            if (!IsAllowed(item, response.enabled) || seen.Contains(item.id)) continue;
                            if (item.kind == "stop_all")
                            {
                                Remember(seen, item.id);
                                StartStopAll();
                                return;
                            }
                            if (Show(item.store)) Remember(seen, item.id);
                        }
                    }
                }
                else if (DateTime.UtcNow - unavailableSince > TimeSpan.FromMinutes(2))
                {
                    return;
                }
                string currentSchedule = FetchScheduleSignature();
                if (currentSchedule != null)
                {
                    if (scheduleSignature != null && scheduleSignature != currentSchedule)
                    {
                        StartScheduleSync();
                    }
                    scheduleSignature = currentSchedule;
                }
                Thread.Sleep(TimeSpan.FromSeconds(3));
            }
        }

        private static string FetchScheduleSignature()
        {
            try
            {
                var request = (HttpWebRequest)WebRequest.Create(ConfigEndpoint);
                request.Proxy = null;
                request.Timeout = 2500;
                request.ReadWriteTimeout = 2500;
                request.UserAgent = "Lontrium-Notifier/1";
                using (var response = (HttpWebResponse)request.GetResponse())
                using (var stream = response.GetResponseStream())
                using (var reader = new StreamReader(stream, Encoding.UTF8))
                {
                    if (response.StatusCode != HttpStatusCode.OK) return null;
                    var config = new JavaScriptSerializer().Deserialize<ConfigResponse>(reader.ReadToEnd());
                    if (config?.values == null) return null;
                    return string.Join("|", config.values.WINDOWS_ECONOMY_SCHEDULE,
                        config.values.RUN_ON_STARTUP, config.values.WINDOWS_WAKE_ON_AC,
                        config.values.SCHEDULER_FIXED_TIMES ?? "",
                        string.Join(",", config.values.STORES ?? new string[0]));
                }
            }
            catch
            {
                return null;
            }
        }

        private static void StartScheduleSync()
        {
            try
            {
                string launcher = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "Start-ClaimerControl.ps1");
                if (!File.Exists(launcher)) return;
                Process.Start(new ProcessStartInfo
                {
                    FileName = "powershell.exe",
                    Arguments = "-NoLogo -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File \"" + launcher + "\" -Action sync-schedule -Language auto",
                    WorkingDirectory = AppDomain.CurrentDomain.BaseDirectory,
                    UseShellExecute = false,
                    CreateNoWindow = true,
                    WindowStyle = ProcessWindowStyle.Hidden,
                });
            }
            catch { }
        }

        private static void StartStopAll()
        {
            try
            {
                string launcher = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "Start-ClaimerControl.ps1");
                if (!File.Exists(launcher)) return;
                Process.Start(new ProcessStartInfo
                {
                    FileName = "powershell.exe",
                    Arguments = "-NoLogo -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File \"" + launcher + "\" -Action stop -Language auto",
                    WorkingDirectory = AppDomain.CurrentDomain.BaseDirectory,
                    UseShellExecute = false,
                    CreateNoWindow = true,
                    WindowStyle = ProcessWindowStyle.Hidden,
                });
            }
            catch { }
        }

        private static EventResponse Fetch()
        {
            try
            {
                var request = (HttpWebRequest)WebRequest.Create(Endpoint);
                request.Proxy = null;
                request.Timeout = 2500;
                request.ReadWriteTimeout = 2500;
                request.UserAgent = "Lontrium-Notifier/1";
                using (var response = (HttpWebResponse)request.GetResponse())
                using (var stream = response.GetResponseStream())
                using (var reader = new StreamReader(stream, Encoding.UTF8))
                {
                    if (response.StatusCode != HttpStatusCode.OK) return null;
                    return new JavaScriptSerializer().Deserialize<EventResponse>(reader.ReadToEnd());
                }
            }
            catch
            {
                return null;
            }
        }

        private static bool IsAllowed(ManualEvent item, bool notificationsEnabled)
        {
            if (item == null || !Guid.TryParseExact(item.id, "N", out _)) return false;
            if (item.kind == "stop_all") return item.store == "system";
            return notificationsEnabled
                && item.kind == "captcha"
                && AllowedStores.Contains(item.store ?? "");
        }

        private static bool Show(string store)
        {
            try
            {
                string language = CultureInfo.CurrentUICulture.TwoLetterISOLanguageName;
                string title = language == "pt" ? "Lontrium — ação necessária"
                    : language == "es" ? "Lontrium — acción necesaria"
                    : "Lontrium — action required";
                string storeName = StoreName(store);
                string body = language == "pt" ? $"A {storeName} está aguardando a resolução de um CAPTCHA."
                    : language == "es" ? $"{storeName} está esperando que resuelvas un CAPTCHA."
                    : $"{storeName} is waiting for you to solve a CAPTCHA.";
                string button = language == "pt" ? "Abrir navegador"
                    : language == "es" ? "Abrir navegador"
                    : "Open browser";
                string image = new Uri(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "Lontrium.png")).AbsoluteUri;
                string xml = "<toast launch=\"" + BrowserUrl + "\"><visual><binding template=\"ToastGeneric\">"
                    + "<text>" + Escape(title) + "</text><text>" + Escape(body) + "</text>"
                    + "<image placement=\"appLogoOverride\" hint-crop=\"circle\" src=\"" + Escape(image) + "\"/>"
                    + "</binding></visual><actions><action content=\"" + Escape(button)
                    + "\" arguments=\"" + BrowserUrl + "\" activationType=\"protocol\"/></actions></toast>";
                var document = new XmlDocument();
                document.LoadXml(xml);
                ToastNotificationManager.CreateToastNotifier(AppId).Show(new ToastNotification(document));
                return true;
            }
            catch
            {
                return false;
            }
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
                default: return char.ToUpperInvariant(store[0]) + store.Substring(1);
            }
        }

        private static string Escape(string value) => SecurityElement.Escape(value) ?? "";

        private static string SeenPath => Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "Lontrium Control", "notifier-events.txt");

        private static HashSet<string> LoadSeen()
        {
            try
            {
                return new HashSet<string>(File.ReadAllLines(SeenPath), StringComparer.Ordinal);
            }
            catch
            {
                return new HashSet<string>(StringComparer.Ordinal);
            }
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

        private sealed class EventResponse
        {
            public bool enabled { get; set; }
            public ManualEvent[] events { get; set; }
        }

        private sealed class ManualEvent
        {
            public string id { get; set; }
            public string kind { get; set; }
            public string store { get; set; }
        }

        private sealed class ConfigResponse
        {
            public ScheduleValues values { get; set; }
        }

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
