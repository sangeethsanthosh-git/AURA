using System;
using System.IO;
using System.Threading.Tasks;
using Windows.Media.Control;
using Windows.Storage.Streams;

public class WindowsMediaController
{
    public static async Task<string> GetCurrentSessionJsonAsync()
    {
        try
        {
            var manager = await GlobalSystemMediaTransportControlsSessionManager.RequestAsync();
            var session = manager.GetCurrentSession();
            if (session == null)
            {
                // Fallback: look through all sessions to find Spotify or any active media session
                var sessions = manager.GetSessions();
                foreach (var s in sessions)
                {
                    if (s != null)
                    {
                        session = s;
                        break;
                    }
                }
            }

            if (session == null)
            {
                return "{\"ok\":true,\"active\":false}";
            }

            var mediaProps = await session.TryGetMediaPropertiesAsync();
            var playbackInfo = session.GetPlaybackInfo();
            var timeline = session.GetTimelineProperties();

            string title = mediaProps != null ? mediaProps.Title : "";
            string artist = mediaProps != null ? mediaProps.Artist : "";
            string album = mediaProps != null ? mediaProps.AlbumTitle : "";
            string appId = session.SourceAppId ?? "";
            string status = playbackInfo != null ? playbackInfo.PlaybackStatus.ToString() : "Closed";
            bool isPlaying = status.Equals("Playing", StringComparison.OrdinalIgnoreCase);

            double posSec = timeline != null ? timeline.Position.TotalSeconds : 0;
            double endSec = timeline != null ? timeline.EndTime.TotalSeconds : 0;

            // Thumbnail
            string thumbBase64 = "";
            if (mediaProps != null && mediaProps.Thumbnail != null)
            {
                try
                {
                    using (var stream = await mediaProps.Thumbnail.OpenReadAsync())
                    using (var netStream = stream.AsStreamForRead())
                    using (var ms = new MemoryStream())
                    {
                        await netStream.CopyToAsync(ms);
                        thumbBase64 = "data:image/jpeg;base64," + Convert.ToBase64String(ms.ToArray());
                    }
                }
                catch { }
            }

            // Clean escape for JSON
            title = EscapeJson(title);
            artist = EscapeJson(artist);
            album = EscapeJson(album);
            appId = EscapeJson(appId);

            return "{" +
                "\"ok\":true," +
                "\"active\":true," +
                "\"title\":\"" + title + "\"," +
                "\"artist\":\"" + artist + "\"," +
                "\"album\":\"" + album + "\"," +
                "\"appId\":\"" + appId + "\"," +
                "\"isPlaying\":" + (isPlaying ? "true" : "false") + "," +
                "\"status\":\"" + status + "\"," +
                "\"progressMs\":" + (int)(posSec * 1000) + "," +
                "\"durationMs\":" + (int)(endSec * 1000) + "," +
                "\"imageUrl\":\"" + thumbBase64 + "\"" +
                "}";
        }
        catch (Exception ex)
        {
            return "{\"ok\":false,\"error\":\"" + EscapeJson(ex.Message) + "\"}";
        }
    }

    public static async Task<string> ControlAsync(string action)
    {
        try
        {
            var manager = await GlobalSystemMediaTransportControlsSessionManager.RequestAsync();
            var session = manager.GetCurrentSession();
            if (session == null)
            {
                var sessions = manager.GetSessions();
                foreach (var s in sessions)
                {
                    if (s != null) { session = s; break; }
                }
            }

            if (session == null)
            {
                return "{\"ok\":false,\"message\":\"No active media session found.\"}";
            }

            bool success = false;
            if (action == "play" || action == "playpause")
            {
                var info = session.GetPlaybackInfo();
                if (info != null && info.PlaybackStatus == GlobalSystemMediaTransportControlsSessionPlaybackStatus.Playing)
                {
                    success = await session.TryPauseAsync();
                }
                else
                {
                    success = await session.TryPlayAsync();
                }
            }
            else if (action == "pause")
            {
                success = await session.TryPauseAsync();
            }
            else if (action == "next")
            {
                success = await session.TrySkipNextAsync();
            }
            else if (action == "previous")
            {
                success = await session.TrySkipPreviousAsync();
            }

            return "{\"ok\":" + (success ? "true" : "false") + "}";
        }
        catch (Exception ex)
        {
            return "{\"ok\":false,\"error\":\"" + EscapeJson(ex.Message) + "\"}";
        }
    }

    private static string EscapeJson(string s)
    {
        if (string.IsNullOrEmpty(s)) return "";
        return s.Replace("\\", "\\\\").Replace("\"", "\\\"").Replace("\r", "").Replace("\n", " ");
    }
}

