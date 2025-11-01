# Device listing and stream testing script
# Run this in the better-voice-typing venv

Write-Host "=== Listing all input devices ===" -ForegroundColor Cyan
python devlist.py

Write-Host "`n=== Testing default device (ID: 1) ===" -ForegroundColor Cyan
python test_stream.py 1

Write-Host "`n=== Testing Input (Sennheiser) device (ID: 45) ===" -ForegroundColor Cyan
python test_stream.py 45

Write-Host "`n=== Checking generated WAV files ===" -ForegroundColor Cyan
Get-ChildItem -Filter "sd_test_*.wav" | ForEach-Object {
    Write-Host "`nFile: $($_.Name)" -ForegroundColor Yellow
    Write-Host "Size: $($_.Length) bytes"
}

Write-Host "`nDone! Check the output above for errors and test the WAV files for audio." -ForegroundColor Green
