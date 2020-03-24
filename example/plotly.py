#!/usr/bin/env python3
import pandas as pd
import plotly.io as pio

## IMPORT-DATA tudocomp eval/tudocomp.log
## IMPORT-DATA low eval/low.txt


# MULTIPLOT(indextype, tabletype) SELECT (mem*8.0)/n AS x, (time*1000*1000.0)/n as y, MULTIPLOT FROM "low" 
# WHERE "action" = 'compression'
# AND "file"  = 'english.1024MB'
# GROUP BY MULTIPLOT,x ORDER BY MULTIPLOT,x
# CONFIG file=json/low.csv type=csv

##
## MULTIPLOT(algo) SELECT (mem*8.0)/n AS x, (time*1000*1000.0)/n as y, MULTIPLOT FROM "tudocomp" 
## WHERE "action" = 'compression'
## AND "file"  = 'english.1024MB'
## GROUP BY MULTIPLOT,x ORDER BY MULTIPLOT,x
## CONFIG file=json/tudocomp.csv type=csv

df = pd.read_csv('json/tudocomp.csv', header=0)
data = [dict(
  type = 'scatter',
  mode = 'markers',
  x = df['x'],
  y = df['y'],
  text = df['title'],
  hoverinfo = 'text',
  opacity = 0.8,
  transforms = [
      dict(
        type = 'groupby',
        groups = df['title'],
    )]
)]


layout = dict(
	title="LZ78 time/mem comparison",
	xaxis = dict(
		title="bits per input character",
		),
	yaxis = dict(
		title="microseconds per input character",
		#        type = 'log'
		),
	)

fig_dict = dict(data=data, layout=layout)
pio.show(fig_dict, validate=False, config={'scrollZoom': True})


# coordinates = eval(open('json/low.json', 'r').read())
# """ coordinates is a list whose entries have type ([String], [(Int, Int)]), where the former [String] is the name and the latter is a list of pair of x/y coordinates. """
#
# fig = px.scatter(x=[0, 1, 2, 3, 4], y=[0, 1, 4, 9, 16])
# fig.show()
#
#
# for key in coordinates:
# 	plt.plot(list(map(lambda row: row[0], coordinates[key])), list(map(lambda row: row[1], coordinates[key])), label = key)
#
# # naming the x axis 
# plt.xlabel('x - axis') 
# # naming the y axis 
# plt.ylabel('y - axis') 
#   
# # show a legend on the plot 
# plt.legend() 
#
#
# # giving a title to my graph 
# plt.title('Graph') 
#   
# # function to show the plot 
# plt.show() 
#
#
