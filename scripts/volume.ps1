param(
    [string]$Action = "get",
    [double]$Value = 0.5
)

$code = @'
using System;
using System.Runtime.InteropServices;

[Guid("5CDF2C82-841E-4546-9722-0CF74078229A"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IAudioEndpointVolume {
    int f(); int g(); int h(); int j();
    int SetMasterVolumeLevelScalar(float fLevel, System.Guid pguidEventContext);
    int k();
    int GetMasterVolumeLevelScalar(out float pfLevel);
    int SetMute(bool bMute, System.Guid pguidEventContext);
    int GetMute(out bool pbMute);
}

[Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDevice {
    int Activate(ref System.Guid id, int clsCtx, System.IntPtr activationParams, out IAudioEndpointVolume aev);
}

[Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDeviceEnumerator {
    int GetDefaultAudioEndpoint(int dataFlow, int role, out IMMDevice endpoint);
}

[ComImport, Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")] class MMDeviceEnumeratorComObject { }

public class AudioController {
    public static float GetVolume() {
        var enumerator = new MMDeviceEnumeratorComObject() as IMMDeviceEnumerator;
        IMMDevice dev = null;
        enumerator.GetDefaultAudioEndpoint(0, 1, out dev);
        var IID = typeof(IAudioEndpointVolume).GUID;
        IAudioEndpointVolume epv = null;
        dev.Activate(ref IID, 23, System.IntPtr.Zero, out epv);
        float vol = 0;
        epv.GetMasterVolumeLevelScalar(out vol);
        return vol;
    }
    public static void SetVolume(float level) {
        var enumerator = new MMDeviceEnumeratorComObject() as IMMDeviceEnumerator;
        IMMDevice dev = null;
        enumerator.GetDefaultAudioEndpoint(0, 1, out dev);
        var IID = typeof(IAudioEndpointVolume).GUID;
        IAudioEndpointVolume epv = null;
        dev.Activate(ref IID, 23, System.IntPtr.Zero, out epv);
        epv.SetMasterVolumeLevelScalar(level, System.Guid.Empty);
    }
    public static bool GetMute() {
        var enumerator = new MMDeviceEnumeratorComObject() as IMMDeviceEnumerator;
        IMMDevice dev = null;
        enumerator.GetDefaultAudioEndpoint(0, 1, out dev);
        var IID = typeof(IAudioEndpointVolume).GUID;
        IAudioEndpointVolume epv = null;
        dev.Activate(ref IID, 23, System.IntPtr.Zero, out epv);
        bool mute = false;
        epv.GetMute(out mute);
        return mute;
    }
    public static void SetMute(bool mute) {
        var enumerator = new MMDeviceEnumeratorComObject() as IMMDeviceEnumerator;
        IMMDevice dev = null;
        enumerator.GetDefaultAudioEndpoint(0, 1, out dev);
        var IID = typeof(IAudioEndpointVolume).GUID;
        IAudioEndpointVolume epv = null;
        dev.Activate(ref IID, 23, System.IntPtr.Zero, out epv);
        epv.SetMute(mute, System.Guid.Empty);
    }
}
'@

try {
    Add-Type -TypeDefinition $code -ErrorAction Stop
} catch {
    # Type might already be added in current session
}

if ($Action -eq "get") {
    $v = [AudioController]::GetVolume()
    $m = [AudioController]::GetMute()
    Write-Output "$([math]::Round($v * 100)),$m"
} elseif ($Action -eq "set") {
    [AudioController]::SetVolume([float]$Value)
    Write-Output "OK"
} elseif ($Action -eq "mute") {
    [AudioController]::SetMute($true)
    Write-Output "OK"
} elseif ($Action -eq "unmute") {
    [AudioController]::SetMute($false)
    Write-Output "OK"
}
