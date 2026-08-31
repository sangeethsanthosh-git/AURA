param (
    [string]$Action = "current"
)

$ErrorActionPreference = "Stop"

try {
    Add-Type -AssemblyName System.Runtime.WindowsRuntime

    $asTaskGeneric = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
        $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
    }

    $asTaskNoResult = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
        $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncAction'
    }

    function Await-Op($asyncOp, $type) {
        if (-not $asyncOp) { return $null }
        $method = $asTaskGeneric.MakeGenericMethod($type)
        $task = $method.Invoke($null, @($asyncOp))
        $task.Wait(5000) | Out-Null
        return $task.Result
    }

    function Await-Action($asyncAction) {
        if (-not $asyncAction) { return }
        $task = $asTaskNoResult.Invoke($null, @($asyncAction))
        $task.Wait(3000) | Out-Null
    }

    $mgrType = [Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager, Windows.Media, ContentType=WindowsRuntime]
    $propsType = [Windows.Media.Control.GlobalSystemMediaTransportControlsSessionMediaProperties, Windows.Media, ContentType=WindowsRuntime]
    $boolType = [bool]

    $op = [Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager]::RequestAsync()
    $manager = Await-Op $op $mgrType

    if (-not $manager) {
        Write-Output '{"ok":true,"active":false}'
        exit 0
    }

    $session = $manager.GetCurrentSession()
    if (-not $session) {
        $sessions = $manager.GetSessions()
        foreach ($s in $sessions) {
            if ($s) {
                $session = $s
                break
            }
        }
    }

    if (-not $session) {
        Write-Output '{"ok":true,"active":false}'
        exit 0
    }

    if ($Action -eq "current") {
        $media = $null
        try {
            $mediaOp = $session.TryGetMediaPropertiesAsync()
            $media = Await-Op $mediaOp $propsType
        } catch { }

        $playback = $session.GetPlaybackInfo()
        $timeline = $session.GetTimelineProperties()

        $title = if ($media) { $media.Title } else { "" }
        $artist = if ($media) { $media.Artist } else { "" }
        $album = if ($media) { $media.AlbumTitle } else { "" }
        $appId = $session.SourceAppId
        $statusStr = if ($playback) { $playback.PlaybackStatus.ToString() } else { "Closed" }
        $isPlaying = ($statusStr -eq "Playing")

        $posMs = if ($timeline) { [int]($timeline.Position.TotalMilliseconds) } else { 0 }
        $durMs = if ($timeline) { [int]($timeline.EndTime.TotalMilliseconds) } else { 0 }

        $thumbBase64 = ""
        if ($media -and $media.Thumbnail) {
            try {
                $streamType = [Windows.Storage.Streams.IRandomAccessStreamWithContentType, Windows.Storage.Streams, ContentType=WindowsRuntime]
                $streamOp = $media.Thumbnail.OpenReadAsync()
                $stream = Await-Op $streamOp $streamType
                if ($stream) {
                    $netStream = [System.IO.WindowsRuntimeStreamExtensions]::AsStreamForRead($stream)
                    $ms = New-Object System.IO.MemoryStream
                    $netStream.CopyTo($ms)
                    $bytes = $ms.ToArray()
                    if ($bytes.Length -gt 0) {
                        $thumbBase64 = "data:image/jpeg;base64," + [Convert]::ToBase64String($bytes)
                    }
                    $ms.Dispose()
                    $netStream.Dispose()
                }
            } catch { }
        }

        $obj = [PSCustomObject]@{
            ok = $true
            active = $true
            title = $title
            artist = $artist
            album = $album
            appId = $appId
            isPlaying = $isPlaying
            status = $statusStr
            progressMs = $posMs
            durationMs = $durMs
            imageUrl = $thumbBase64
        }
        $obj | ConvertTo-Json -Compress
        exit 0
    }

    if ($Action -eq "play" -or $Action -eq "playpause") {
        $playback = $session.GetPlaybackInfo()
        if ($playback -and $playback.PlaybackStatus.ToString() -eq "Playing") {
            $act = $session.TryPauseAsync()
            $res = Await-Op $act $boolType
        } else {
            $act = $session.TryPlayAsync()
            $res = Await-Op $act $boolType
        }
        Write-Output '{"ok":true}'
        exit 0
    }

    if ($Action -eq "pause") {
        $act = $session.TryPauseAsync()
        $res = Await-Op $act $boolType
        Write-Output '{"ok":true}'
        exit 0
    }

    if ($Action -eq "next") {
        $act = $session.TrySkipNextAsync()
        $res = Await-Op $act $boolType
        Write-Output '{"ok":true}'
        exit 0
    }

    if ($Action -eq "previous") {
        $act = $session.TrySkipPreviousAsync()
        $res = Await-Op $act $boolType
        Write-Output '{"ok":true}'
        exit 0
    }

    Write-Output '{"ok":false,"message":"Unknown action"}'
} catch {
    $err = $_.Exception.Message
    Write-Output ("{`"ok`":false,`"error`":`"" + $err.Replace('"', '\"') + "`"}")
}

