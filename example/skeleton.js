/// IMPORT-DATA low eval/low.txt
///
/// MULTIPLOT(indextype, tabletype) SELECT time AS x, mem as y, MULTIPLOT FROM "low" 
/// WHERE "action" = 'compression'
/// AND "file"  = 'english.1024MB'
/// GROUP BY MULTIPLOT,x ORDER BY MULTIPLOT,x
/// CONFIG file=json/low.json

