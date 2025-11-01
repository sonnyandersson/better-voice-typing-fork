# Activate virtual environment
& ".\.venv\Scripts\Activate.ps1"

# Run device listing
Write-Host "=== Available Input Devices ===`n"
python devlist.py

# Test default device (ID: 1)
Write-Host "`n=== Testing Device ID 1 (default) ===`n"
python test_stream.py 1

# Test Input Sennheiser (ID: 45)
Write-Host "`n=== Testing Device ID 45 (Input Sennheiser) ===`n"
python test_stream.py 45

# List any generated WAV files
Write-Host "`n=== Generated test files ===`n"
Get-ChildItem sd_test_*.wav -ErrorAction SilentlyContinue | Select-Object Name, Length
