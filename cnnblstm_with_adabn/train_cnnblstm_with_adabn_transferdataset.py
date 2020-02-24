import torch
# local class
import sys
sys.path.append("..")
import tools
from cnnblstm_with_adabn import cnnblstm_with_adabn

TRAIN_PATH = r"../dataset/transfer_train"
TEST_PATH = r"../dataset/transfer_test"

if __name__ == '__main__':
	torch.manual_seed(2)

	# whether use cuda
	use_cuda = torch.cuda.is_available()
	if use_cuda:
		m_cnnblstm_with_adabn = cnnblstm_with_adabn(use_cuda = 1, params_dir = "./params_transferdataset").cuda()
	else:
		m_cnnblstm_with_adabn = cnnblstm_with_adabn(use_cuda = 0, params_dir = "./params_transferdataset")
	print(m_cnnblstm_with_adabn)
	# get train_x, train_y
	Y, segments, maxlen_seg, n_files, seq_length = tools.getAllData(TRAIN_PATH)
	X_all, y_all, _ = tools.transferData(Y, segments, n_files, seq_length)
	train_x = torch.from_numpy(X_all)
	train_y = torch.from_numpy(y_all)
	train_data = torch.utils.data.TensorDataset(train_x, train_y)
	# trainAllLayers
	m_cnnblstm_with_adabn.trainAllLayers(train_data)
	# get test_x, test_y
	Y, segments, maxlen_seg, n_files, seq_length = tools.getAllData(TEST_PATH)
	X_all, y_all, _ = tools.transferData(Y, segments, n_files, seq_length)
	test_x = torch.from_numpy(X_all)
	test_y = torch.from_numpy(y_all)
	# get test accuracy
	m_cnnblstm_with_adabn.getTestAccuracy(test_x, test_y)
