$ErrorActionPreference = 'Stop'
$demoScenes = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'scenes.json') -Raw -Encoding utf8 | ConvertFrom-Json
$demoAudioFolder = Join-Path $PSScriptRoot '..\..\cache\video\audio'
New-Item -ItemType Directory -Path $demoAudioFolder -Force | Out-Null
$demoVoice = New-Object -ComObject SAPI.SpVoice
$demoVoice.Rate = 1
$demoVoice.Volume = 100
$demoVoiceInfo = $demoVoice.Voice.GetDescription()
$sceneNumber = 0
foreach ($scene in $demoScenes) {
    $sceneNumber++
    $demoStream = New-Object -ComObject SAPI.SpFileStream
    try {
        $demoStream.Open((Join-Path $demoAudioFolder ('{0:d2}.wav' -f $sceneNumber)), 3, $false)
        $demoVoice.AudioOutputStream = $demoStream
        [void]$demoVoice.Speak($scene.say)
    } finally {
        $demoStream.Close()
    }
}
Write-Output "Narration generated using local synthetic voice: $demoVoiceInfo"
