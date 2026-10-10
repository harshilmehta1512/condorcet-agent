$ErrorActionPreference = 'Stop'
$videoFolder = $PSScriptRoot
$demoScenes = Get-Content -LiteralPath (Join-Path $videoFolder 'scenes.json') -Raw -Encoding utf8 | ConvertFrom-Json
$demoVoice = New-Object -ComObject SAPI.SpVoice
$demoVoice.Rate = 1
$sceneNumber = 0
foreach ($scene in $demoScenes) {
    $sceneNumber++
    $demoStream = New-Object -ComObject SAPI.SpFileStream
    try {
        $demoStream.Open((Join-Path $videoFolder ('{0:d2}.wav' -f $sceneNumber)), 3, $false)
        $demoVoice.AudioOutputStream = $demoStream
        [void]$demoVoice.Speak($scene.say)
    } finally {
        $demoStream.Close()
    }
}
Write-Output 'Narration generated. Run python ui/video/build_video.py from the repository root.'
