# Measured linear vs power-0.75 player comparison (35 cases)

Retained checkpoint `12063` (Oct17) for Career raw and recovered concurrent discounted 3-Year raw. Current published 3-Year/Career indices from `12072` (same Oct17 publication window); **formal exact-State identity remains unproven**. All 35 identities from saved stratified cohort. Diagnostic anchors: 3-Year 750; Career 2000. These are not approved historical anchors.

## Player-by-player results

|Player|Position|Raw 3Y|Current 3Y|Linear 3Y|Power .75 3Y|Raw Career|Current Career|Linear Career|Power .75 Career|
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
|Tyler Huntley (7083)|QB|11.4|17|152|433|71.04|1677|355|818|
|Malik Willis (8161)|QB|350.59|3300|4675|5653|743.75|9012|3719|4762|
|Jordan Love (6804)|QB|473.82|5229|6318|7086|1301.09|9641|6505|7244|
|Jameis Winston (2306)|QB|16.46|32|219|570|49.34|898|247|622|
|Jacoby Brissett (3257)|QB|298.38|2516|3978|5009|463.89|7784|2319|3342|
|Jared Goff (3163)|QB|521.3|5602|6951|7612|1224.33|9551|6122|6921|
|Jalon Daniels (13425)|QB|18.06|34|241|611|212.71|5000|1064|1862|
|Riley Leonard (12470)|QB|31.29|55|417|923|369.58|7036|1848|2818|
|Cam Ward (12522)|QB|400.17|3665|5336|6243|1440.45|9790|7202|7818|
|Ty Johnson (6039)|RB|50.45|184|673|1321|64.57|1347|323|762|
|Rachaad White (8136)|RB|198.28|1456|2644|3687|260.12|5689|1301|2166|
|Kyren Williams (8150)|RB|348.09|3204|4641|5623|533.66|8084|2668|3713|
|James Conner (4137)|RB|10.01|16|133|393|13.22|30|66|232|
|Aaron Jones (4199)|RB|116.2|981|1549|2469|131.84|3204|659|1301|
|Derrick Henry (3198)|RB|335.26|3057|4470|5467|389.92|7246|1950|2934|
|Nicholas Singleton (13288)|RB|48.83|175|651|1289|74.33|1796|372|846|
|Mike Washington (13305)|RB|111.37|962|1485|2392|159.8|3832|799|1503|
|Jeremiyah Love (13287)|RB|381.93|3549|5092|6028|561.8|8353|2809|3858|
|Luke Schoonmaker (10871)|TE|23.38|41|312|742|57.91|1138|290|702|
|T.J. Hockenson (5844)|TE|121.21|1007|1616|2549|175.69|4251|878|1614|
|Pat Freiermuth (7600)|TE|140.12|1150|1868|2842|225.88|5269|1129|1948|
|Durham Smythe (5008)|TE|24.06|43|321|758|32.52|449|163|455|
|Hunter Henry (3214)|TE|124.52|1021|1660|2601|186.51|4611|933|1688|
|George Kittle (4217)|TE|161.43|1277|2152|3160|249.85|5539|1249|2101|
|Elijah Higgins (10231)|TE|40.48|123|540|1120|90.48|2455|452|981|
|Theo Johnson (11597)|TE|69.1|329|921|1672|181|4431|905|1650|
|Sam LaPorta (10859)|TE|196.2|1446|2616|3658|377.26|7096|1886|2862|
|Darnell Mooney (7090)|WR|57.22|254|763|1452|83.88|2126|419|927|
|Courtland Sutton (5045)|WR|194.3|1420|2591|3631|259.53|5659|1298|2162|
|Rashee Rice (10229)|WR|303.05|2572|4041|5068|445.28|7605|2226|3241|
|Cooper Kupp (4039)|WR|63.58|281|848|1571|76.16|1886|381|862|
|Stefon Diggs (2449)|WR|156.18|1256|2082|3083|184.99|4551|925|1677|
|Malik Benson (13329)|WR|42.87|138|572|1169|94.38|2515|472|1012|
|Ja'Kobi Lane (13293)|WR|107.15|917|1429|2324|210.8|4880|1054|1850|
|Brian Thomas (11631)|WR|219.74|1607|2930|3982|492.95|7874|2465|3498|

## Actual economic separations in illustrative player decisions

|Pair (A vs B)|3Y raw A/B|Linear 3Y gap|Power 3Y gap|Career raw A/B|Linear Career gap|Power Career gap|
|---|---:|---:|---:|---:|---:|---:|
|Derrick Henry vs Riley Leonard|10.71x|4053|4544|1.06x|102|116|
|Jordan Love vs Cam Ward|1.18x|982|843|0.90x|-697|-574|
|Derrick Henry vs Kyren Williams|0.96x|-171|-156|0.73x|-718|-779|
|Brian Thomas vs Stefon Diggs|1.41x|848|899|2.66x|1540|1821|
|Jared Goff vs Jordan Love|1.10x|633|526|0.94x|-383|-323|

## Interpretation

- Both transforms preserve raw within-horizon ordering (aside from clamping/rounding). Neither can discover a superior ranking or new football signal.
- Linear produces scores directly proportional to raw modeled value until ceiling. Power .75 makes small and medium contributions more legible at the cost of ratio fidelity.
- A score difference **across horizons** or versus Market **cannot be interpreted as economic surplus** merely because all scores are 0–10,000.
- The power transformation appears appealing for readable labels but is **not yet proven optimal**. Correct anchor choice, clipping frequency, temporal stability, zero/unavailable handling, and objective validation remain mandatory.
- Do not change raw Shapley, normalize artificially by position, impose Career>=3-Year, merge, deploy, or alter production.
