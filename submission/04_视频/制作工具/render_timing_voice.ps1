param([string]$StoryFile,[string]$OutputDirectory,[int]$Rate=1)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Speech
$taskScenes=(Get-Content -LiteralPath $StoryFile -Raw -Encoding utf8 | ConvertFrom-Json).scenes
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
$taskSpeech=New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
 $taskSpeech.SelectVoice('Microsoft Huihui Desktop');$taskSpeech.Rate=$Rate;$taskSpeech.Volume=100
 $taskFormat=New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(16000,[System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen,[System.Speech.AudioFormat.AudioChannel]::Mono)
 foreach($taskScene in $taskScenes){
  $taskSpeech.SetOutputToWaveFile((Join-Path $OutputDirectory ($taskScene.id+'.wav')),$taskFormat)
  $taskSpeech.Speak($taskScene.narration.Replace('Sim2Act','Sim to Act'))
  $taskSpeech.SetOutputToNull()
 }
} finally {$taskSpeech.Dispose()}
$taskRecord=@{source_sha256=(Get-FileHash -LiteralPath $StoryFile -Algorithm SHA256).Hash.ToLowerInvariant();voice='Microsoft Huihui Desktop';rate=$Rate;scenes=@($taskScenes | ForEach-Object { @{id=$_.id;narration=$_.narration} })}
$taskRecord | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $OutputDirectory 'voice-source.json') -Encoding utf8
Write-Output '27 local timing voice clips rendered; no playback or model request.'
