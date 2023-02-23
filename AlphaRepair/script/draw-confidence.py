import numpy as np
from scipy import stats
from typing import List, Tuple, Dict, Set
import matplotlib.pyplot as plt

def get_confidence_interval(data: List[List[int]]) -> Tuple[List[float], List[float]]
  # data = [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]]
  # Calculate the mean and standard deviation of each sublist
  means = [np.mean(sublist) for sublist in data]
  stds = [np.std(sublist, ddof=1) for sublist in data]

  # Calculate the 95% confidence interval for each mean
  n = len(data[0])  # sample size
  conf_intervals = [stats.t.interval(0.95, df=n-1, loc=mean, scale=std/np.sqrt(n)) for mean, std in zip(means, stds)]

  # Return the confidence intervals
  lower = list()
  upper = list()
  for i, interval in enumerate(conf_intervals):
    lower.append(interval[0])
    upper.append(interval[1])
  return lower, upper, means

x = range(301)
y: List[List[int]] = list()
for i in x:
  tmp_list = list()
  for j in range(50):
    tmp_list.append()
  y.append(tmp_list)
y_lower, y_upper, y_means = get_confidence_interval(y)
plt.plot(x, y_means)
plt.fill_between(x, y_lower, y_upper, alpha=0.3)
plt.savefig("result.pdf")