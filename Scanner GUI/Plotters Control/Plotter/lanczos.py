from __future__ import division
import itertools
import numpy as np

def deriv(f, x, N, delta):
	if N%2 == 0:
		N += 1
	else:
		pass
	m = int((N - 1) / 2)
	denom = m * (m + 1) * (2*m + 1)
	k = np.arange(1, 2*(m + 1))
	lanc = (3  * k) / (denom * delta)
	df0 = []
	df1 = []
	df = [sum(lanc[j-1]*(f[i+j] - f[i-j]) for j in range(1, m+1)) for i in range(m-1, len(f) - m)]
	first_dats = f[0:N]
	last_dats = f[len(f) - N: len(f)]
	first_fit = np.polyfit(x[0:N], first_dats, 2)
	last_fit = np.polyfit(x[len(f) - N: len(f)], last_dats, 2)
	for i in range(0, m-1):
		df0.append (first_fit[1] + 2 * first_fit[0] * x[i]) 
	for i in range(len(f) - m, len(f)):
		df1.append(last_fit[1] + 2 * last_fit[0] * x[i])

	return list(itertools.chain(df0, df, df1))



