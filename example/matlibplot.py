import matplotlib.pyplot as plt 
 

## IMPORT-DATA low eval/low.txt
##
## MULTIPLOT(indextype, tabletype) SELECT time AS x, mem as y, MULTIPLOT FROM "low" 
## WHERE "action" = 'compression'
## AND "file"  = 'english.1024MB'
## GROUP BY MULTIPLOT,x ORDER BY MULTIPLOT,x
## CONFIG file=json/low.json

coordinates = eval(open('json/low.json', 'r').read())
""" coordinates is a list whose entries have type ([String], [(Int, Int)]), where the former [String] is the name and the latter is a list of pair of x/y coordinates. """


for key in coordinates:
	plt.plot(list(map(lambda row: row[0], coordinates[key])), list(map(lambda row: row[1], coordinates[key])), label = key)

# naming the x axis 
plt.xlabel('x - axis') 
# naming the y axis 
plt.ylabel('y - axis') 
  
# show a legend on the plot 
plt.legend() 


# giving a title to my graph 
plt.title('Graph') 
  
# function to show the plot 
plt.show() 


