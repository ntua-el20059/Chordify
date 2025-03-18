for i in {2..9}; do
    scp -r team_3-vm$((i/2)):~/Chordify ~/Chordify/node0$i
done