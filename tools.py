import os
import csv
# import cv2
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
# local class
import sys
sys.path.append("../network")
# import PCA as mPCA
from sklearn.decomposition import PCA

def getAllData(path, if_quiet = 0):
	n_files = 0
	label_index = np.zeros((10, 10))
	label_index[0] = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
	label_index[1] = [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
	label_index[2] = [1, 3, 5, 7, 9, 0, 2, 4, 6, 8]
	label_index[3] = [8, 6, 4, 2, 0, 9, 7, 5, 3, 1]
	label_index[4] = [0, 3, 6, 9, 2, 5, 8, 1, 4, 7]
	label_index[5] = [7, 4, 1, 8, 5, 2, 9, 6, 3, 0]
	label_index[6] = [0, 4, 8, 2, 6, 1, 5, 9, 3, 7]
	label_index[7] = [7, 3, 9, 5, 1, 6, 2, 8, 4, 0]
	label_index[8] = [0, 5, 1, 6, 2, 7, 3, 8, 4, 9]
	label_index[9] = [0, 0, 6, 6, 0, 6, 6, 0, 0, 6]
	for dir_path, dir_names, file_names in os.walk(path):
		for filename in file_names:
			n_files += 1

	set_dataframe = [0] * n_files
	label = np.zeros((n_files))
	index = 0
	for dir_path, dir_names, file_names in os.walk(path):
		for filename in file_names:
			dataframe1 = pd.read_csv(os.path.join(dir_path, filename), sep = ",")
			set_dataframe[index] = pd.DataFrame(dataframe1.iloc[5:-5].values, columns = dataframe1.columns)
			dataframe = dataframe1[5:-5].reset_index(drop = True)
			label[index] = filename[0]
			index += 1

	maxlen_seg = 0
	segments = [0] * n_files
	if (if_quiet == 1):
		seq_length = np.zeros((n_files, 20))
		Y = np.zeros((n_files, 2, 20))
	else:
		seq_length = np.zeros((n_files, 10))
		Y = np.zeros((n_files, 2, 10))

	for file_index in range(n_files):
		dataframe = set_dataframe[file_index]
		data_seg = np.zeros((10, 2, 2))

		data_seg[0][0][0] = 0
		current_index = 0
		flag = 0

		for row in range(dataframe.shape[0]):
			if (dataframe.Keydown[row] != str(-1)):
				if (flag == 0):
					data_seg[current_index][0][1] = row - 1
					data_seg[current_index][1][0] = row + 1
					flag = (flag + 1) % 2
				else:
					data_seg[current_index][1][1] = row - 1
					current_index += 1
					data_seg[current_index][0][0] = row + 1
					flag = (flag + 1) % 2
		data_seg[9][1][1] = dataframe.shape[0] - 1

		for i in range(10):
			if ((data_seg[i][0][1] - data_seg[i][0][0]) > maxlen_seg):
				maxlen_seg = data_seg[i][0][1] - data_seg[i][0][0]
			if ((data_seg[i][1][1] - data_seg[i][1][0]) > maxlen_seg):
				maxlen_seg = data_seg[i][1][1] - data_seg[i][1][0]

		n_segs = np.zeros((10, int(maxlen_seg), 3))
		quiet_segs = np.zeros((10, int(maxlen_seg), 3))

		for i in range(10):
			if (i == 0):
				n_segs[i][0:int(data_seg[i][0][1]) - int(data_seg[i][0][0])] = dataframe[['ACCx', 'ACCy', 'ACCz']][int(data_seg[i][0][0]):int(data_seg[i][0][1])]
			else:
				n_segs[i][0:(int(data_seg[i][0][1]) - int(data_seg[i][0][0]))] = dataframe[['ACCx', 'ACCy', 'ACCz']][int(data_seg[i][0][0]):int(data_seg[i][0][1])]
			if (i == 9):
				quiet_segs[i][0:(int(data_seg[i][1][1]) - int(data_seg[i][1][0]))] = dataframe[['ACCx', 'ACCy', 'ACCz']][int(data_seg[i][1][0]):int(data_seg[i][1][1])]
			else:
				quiet_segs[i][0:(int(data_seg[i][1][1]) - int(data_seg[i][1][0]))] = dataframe[['ACCx', 'ACCy', 'ACCz']][int(data_seg[i][1][0]):int(data_seg[i][1][1])]
		if (if_quiet == 1):
			segments[file_index] = np.zeros((20, int(maxlen_seg), 3))
			for i in range(10):
				segments[file_index][2 * i][0:n_segs[i].shape[0]] = n_segs[i]
				Y[file_index][0][2 * i] = i
				Y[file_index][1][2 * i] = data_seg[i][0][1] - data_seg[i][0][0]
			for i in range(10):
				segments[file_index][2 * i + 1][0:quiet_segs[i].shape[0]]=quiet_segs[i]
				Y[file_index][0][2 * i + 1] = -1
				Y[file_index][1][2 * i + 1] = data_seg[i][1][1] - data_seg[i][1][0]

			seq_length[file_index] = Y[file_index][1]
		else:
			segments[file_index] = np.zeros((10, int(maxlen_seg), 3))
			for i in range(10):
				segments[file_index][i][0:n_segs[i].shape[0]] = StandardScaler().fit_transform(n_segs[i])
				Y[file_index][0][i] = label_index[int(label[file_index])][i]
				Y[file_index][1][i] = data_seg[i][0][1] - data_seg[i][0][0]
			seq_length[file_index]=Y[file_index][1]
	return (Y, segments, maxlen_seg, n_files, seq_length)

def transferData(Y, segments, n_files, seq_length, maxlen = 800):
	y_all = np.zeros((n_files * 10, ), dtype = np.int64)
	X_all = np.zeros((n_files * 10, int(maxlen), 3), dtype = np.float32)
	X_all_T = np.zeros((n_files * 10, 3, int(maxlen)), dtype = np.float32)
	for i in range(n_files):
		y_all[10 * i:10 * (i + 1)] = Y[i][0]
		for j in range(10):
			temp = segments[i][j][:, ]
			X_all[10 * i + j][0:segments[i][j].shape[0], :] = temp
	seq_length = seq_length.reshape(n_files * 10)
	for i in range(X_all.shape[0]):
		X_all_T[i] = X_all[i].T
	return (X_all_T, y_all, seq_length)

def allZeroIndex(Xs_item):
	for i in range(Xs_item.shape[0]):
		flag = 0
		for j in range(Xs_item.shape[1]):
			if Xs_item[i, j] != 0:
				flag = 1
				break
		if flag == 0:		# all zeros
			return i
	return Xs_item.shape[0]

def Kalman_Xs(Xs):
	return Xs
	# TODO
	"""
	Xs_new = []
	for i in range(Xs.shape[0]):
		Xsi_new = []
		Xsi_T = Xs[i, :, :].T.astype(np.float32)	# 800 x 3
		# get new kalman
		kalman = cv2.KalmanFilter(6, 3)
		# init matrix
		kalman.measurementMatrix = np.array([[1, 0, 0, 0, 0, 0], [0, 1, 0, 0, 0, 0], [0, 0, 1, 0, 0, 0]], np.float32)
		kalman.transitionMatrix = np.array([[1, 0, 0, 1, 0, 0], [0, 1, 0, 0, 1, 0], [0, 0, 1, 0, 0, 1], [0, 0, 0, 1, 0, 0], [0, 0, 0, 0, 1, 0], [0, 0, 0, 0 ,0 ,1]], np.float32)
		kalman.processNoiseCov = 0.03 * np.array([[1, 0, 0, 0, 0, 0], [0, 1, 0, 0, 0, 0], [0, 0, 1, 0, 0, 0], [0, 0, 0, 1, 0, 0], [0, 0, 0, 0, 1, 0], [0, 0, 0, 0 ,0 ,1]], np.float32)
		for j in range(Xsi_T.shape[0]):
			Xij = Xsi_T[j, :]	# 1 x 3
			# print(Xij.shape, type(Xij))
			Xij = Xij.reshape(3, 1)
			kalman.correct(Xij)
			# print(Xij)
			Xij_new = kalman.predict()[0:3]
			# print(Xij_new, end = "\n\n")
			Xsi_new.append(Xij_new)
		Xsi_new = np.array(Xsi_new, dtype = np.float32)
		Xs_new.append(Xsi_new.T.reshape(3, 800))
	Xs_new = np.array(Xs_new)
	# print(Xs_new.shape)
	return Xs_new
	"""

def PCA_Xs(Xs):
	"""
	Xs: (20 ,3, 800)
	"""
	print(Xs.shape)
	# pca = mPCA.PCA(target_dimension = 3)
	pca = PCA(n_components = 3)
	Xs_new = []
	for i in range(Xs.shape[0]):
		# print(Xs[i])
		Xsi_T = Xs[i].T
		"""
		tail = allZeroIndex(Xsi_T)
		# print(tail, Xsi_T.shape[0] - tail)
		# Xsi_new = pca.process(Xsi_T[:tail, :])
		Xsi_new = pca.fit_transform(Xsi_T[:tail, :])
		Xsi_new = np.pad(Xsi_new, ((0, Xsi_T.shape[0] - tail), (0, 0)), "constant", constant_values = (0, 0))
		"""
		Xsi_new = pca.fit_transform(Xsi_T)
		# print(Xsi_new.shape)
		# print(Xsi_new)
		Xs_new.append(Xsi_new.T)
	Xs_new = np.array(Xs_new)
	return Xs_new

def z_score(x, axis = 0):
	x = np.array(x).astype(float)
	xr = np.rollaxis(x, axis = axis)
	xr -= np.mean(x, axis = axis)
	xr /= np.std(x, axis = axis)
	# print(x)
	return x

