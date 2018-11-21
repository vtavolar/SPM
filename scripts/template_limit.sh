cd [CMSSW]
eval `scramv1 runtime -sh`
[ -d SPM ] || mkdir SPM
cd SPM
[ -d [BUNDLE] ] || mkdir [BUNDLE]
cd [BUNDLE]
cp [BUNDLEDIR]/[BUNDLE]/cards/[CARD] [CARD]
combine [CMD] [CARD] -n [CARD] -m [MASS1] -s [MASS2]
mv higgsCombine[CARD].*.mH[MASS1].[MASS2].root [BUNDLEDIR]/[BUNDLE]/limits
