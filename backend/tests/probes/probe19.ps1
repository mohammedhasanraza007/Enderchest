# Probe 19: building the TEST app never changes the image run.bat starts. run.bat does not build;
# it starts whatever enderchest-app:latest is. If the test stack shared that tag, every test run
# (from any worktree, finished or not) would decide what the next run.bat puts on the owner's data.
# The probe forces a new test image (a unique BUILD_DATE) and needs the live tag to stay put.
. "$PSScriptRoot\lib.ps1"
$liveTag = 'enderchest-app:latest'
$testTag = 'enderchest-app-test:latest'
$before = Dk image inspect -f '{{.Id}}' $liveTag
[void](Dc build --build-arg "BUILD_DATE=probe19-$(Get-Date -Format 'yyyyMMddHHmmss')" app)
$built = ($script:LastExit -eq 0)
$after = Dk image inspect -f '{{.Id}}' $liveTag
$test = Dk image inspect -f '{{.Id}}' $testTag
$testExists = ($script:LastExit -eq 0)
$ok = Result 19 ($built -and $testExists -and ($before -eq $after)) "test build ok=$built; test tag exists=$testExists; live tag before=$($before.Substring(0, [Math]::Min(19, $before.Length))) after=$($after.Substring(0, [Math]::Min(19, $after.Length)))"
exit $(if ($ok) { 0 } else { 1 })
