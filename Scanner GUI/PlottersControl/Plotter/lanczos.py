from __future__ import division
import itertools
import numpy as np
import math

def deriv(Data, x, NumberOfSide, delta, order = 1, EdgeNumber = 10):
	NumberOfSide = int(NumberOfSide)
	EdgeNumber = int(EdgeNumber)
	order = int(order)
	denom = NumberOfSide * (NumberOfSide + 1) * (2*NumberOfSide + 1)#denominator for the weight
	k = np.arange(1, 2*(NumberOfSide + 1))
	lanc = (3  * k) / (denom * delta)#weight
	df0 = []
	df1 = []
	df = [sum(lanc[j-1]*(Data[i+j] - Data[i-j]) for j in range(1, NumberOfSide + 1)) for i in range(NumberOfSide, len(Data) - NumberOfSide)]
	first_dats = Data[0: EdgeNumber]
	last_dats = Data[len(Data) - EdgeNumber: len(Data)]
	first_fit = np.polyfit(x[0: EdgeNumber], first_dats, order)
	last_fit = np.polyfit(x[len(Data) - EdgeNumber: len(Data)], last_dats, order)
	for i in range(0, NumberOfSide):
		deriv = 0
		for j in range(order):
			deriv += first_fit[j] * x[i] ** (order - j - 1 ) * (order - j)
		df0.append(deriv) 
	for i in range(len(Data) - NumberOfSide, len(Data)):
		deriv = 0
		for j in range(order):
			deriv += last_fit[j] * x[i] ** (order - j - 1 ) * (order - j)
		df1.append(deriv)

	return list(itertools.chain(df0, df, df1))



