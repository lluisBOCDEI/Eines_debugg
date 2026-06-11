set terminal qt enhanced persist
set title "n equally spaced points on the unit circle"
set xlabel "x"
set ylabel "y"
set grid
set key off
set size ratio -1
set xrange [-1.1:1.1]
set yrange [-1.1:1.1]

# Circle outline via parametric plot
set parametric
plot \
    cos(t), sin(t) with lines title "Unit Circle", \
    "data.tsv" using 1:2 with points pt 7 ps 1.5 title "Points"
