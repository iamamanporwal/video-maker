import json;V=json.load(open('out/words.json'));W=V['words'];L=V['lines']
ws=lambda k,i=0:0.15+W[L[k][0]+i][0]
we=lambda k:0.15+W[L[k][1]-1][1]
ts=[1.0,ws('h2',8)+0.4,ws('h3')+0.3,ws('h3')+1.8,ws('h4')+0.3,ws('h4')+1.6,ws('b1')+0.8,ws('b1')+4,ws('b2')+0.5,ws('b2',4)+0.3,ws('b2',6)+0.3,ws('b2',7)+0.5,ws('b2',11)+0.2,ws('b2',12)+0.3,ws('b3')+1.0,ws('b3')+4.5,ws('b4')+0.5,ws('b4',5)+0.2,ws('b4',7)+0.2,ws('b4',8)+0.2,ws('b4',9)+1.0,ws('b5')+2.5,ws('b5')+5,ws('p1')+0.6,ws('p2',3)+0.4,ws('p2',6)+1.0,ws('p3',9),ws('p3',12)+0.3,ws('p3',12)+1.2,ws('p4')+1.0,we('p4')+0.3,we('p4')+0.8]
print(','.join(f'{t:.2f}' for t in ts))
