CMSSW="[CMSSW]"
BUNDLE="[BUNDLE]"
BUNDLEDIR="[BUNDLEDIR]"
POOLDIR="[POOLDIR]"
CARDSDIR="[CARDSDIR]"
PACKAGES=( [PACKAGES] )
CARD="[CARD]"
NCARDS=${#PACKAGES[@]}
cd $CMSSW
eval `scramv1 runtime -sh`
[ -d SPM ] || mkdir SPM
cd SPM
[ -d $BUNDLE ] || mkdir $BUNDLE
cd $BUNDLE
PROCS=""
COUNT=0
for EL in "${PACKAGES[@]}"; do
	cp $POOLDIR/$EL/$CARDSDIR/$CARD ${EL}_${CARD}
    let COUNT=COUNT+1 
    PROCS+="Name${COUNT-1}=${EL}_${CARD} "
done
ls
echo $PROCS
eval `combineCards.py -S $PROCS > $CARD`
eval `mv $CARD $BUNDLEDIR/$BUNDLE/cards/`
