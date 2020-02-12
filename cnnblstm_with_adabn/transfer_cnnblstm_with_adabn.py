import os
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.autograd import Variable
# local class
from cnnblstm_with_adabn import cnnblstm_with_adabn
from AdaBN import AdaBN

class transfer_cnnblstm_with_adabn(nn.Module):
	PARAMS_FILE = "params.pkl"
	NET1_ADABN = "net1_adabn"
	NET2_ADABN = "net2_adabn"
	NET3_ADABN = "net3_adabn"

	def __init__(self, time_steps = 800, n_features = 3, n_outputs = 10, use_cuda = 0, params_dir = "./params", transfer_params_dir = "./transfer_params"):
		super(transfer_cnnblstm_with_adabn, self).__init__()

		self.transfer_params_dir = transfer_params_dir
		if not os.path.exists(self.transfer_params_dir):
			os.mkdir(self.transfer_params_dir)

		self.time_steps = time_steps
		self.n_features = n_features
		self.n_outputs = n_outputs
		self.use_cuda = use_cuda

		self.n_filters = 128
		self.n_hidden = 150
		self.bidirectional = True

		self.m_cnnblstm_with_adabn = cnnblstm_with_adabn(time_steps = self.time_steps, n_features = self.n_features, n_outputs = self.n_outputs, use_cuda = self.use_cuda, params_dir = params_dir).get_model(pre_trained = True)
		self.m_cnnblstm_with_adabn.net1_adabn = AdaBN(self.n_filters, variables_dir = os.path.join(self.transfer_params_dir, transfer_cnnblstm_with_adabn.NET1_ADABN))
		if self.bidirectional:
			self.m_cnnblstm_with_adabn.net2_adabn = AdaBN(self.n_hidden * 2, variables_dir = os.path.join(self.transfer_params_dir, transfer_cnnblstm_with_adabn.NET2_ADABN))
		else:
			self.m_cnnblstm_with_adabn.net2_adabn = AdaBN(self.n_hidden, variables_dir = os.path.join(self.transfer_params_dir, transfer_cnnblstm_with_adabn.NET2_ADABN))
		self.m_cnnblstm_with_adabn.net3_adabn = AdaBN(50, variables_dir = os.path.join(self.transfer_params_dir, transfer_cnnblstm_with_adabn.NET3_ADABN))

	def forward(self, input):
		return self.m_cnnblstm_with_adabn(input)

	def init_partial_weights(self):
		self.m_cnnblstm_with_adabn.net1_adabn.reset_parameters()
		self.m_cnnblstm_with_adabn.net2_adabn.reset_parameters()
		self.m_cnnblstm_with_adabn.net3_adabn.reset_parameters()

	def update_adabn_running_stats(self):
		self.m_cnnblstm_with_adabn.net1_adabn.update_running_stats()
		self.m_cnnblstm_with_adabn.net2_adabn.update_running_stats()
		self.m_cnnblstm_with_adabn.net3_adabn.update_running_stats()

	def trainAllLayers(self, train_data, learning_rate = 0.001, n_epoches = 10, batch_size = 20, shuffle = True):
		# Data Loader for easy mini-batch return in training
		train_loader = torch.utils.data.DataLoader(dataset = train_data, batch_size = batch_size, shuffle = shuffle)
		# optimize all adabn parameters
		params = [{"params": model.parameters()} for model in self.m_cnnblstm_with_adabn.children() if model in [self.m_cnnblstm_with_adabn.net1_adabn, self.m_cnnblstm_with_adabn.net2_adabn, self.m_cnnblstm_with_adabn.net3_adabn]]
		optimizer = torch.optim.Adam(params, lr = learning_rate)
		# the target label is not one-hotted
		loss_func = nn.CrossEntropyLoss()

		# init params
		self.init_partial_weights()

		# load params
		self.load_params()

		# set train mode True
		self.train()

		# training and testing
		for epoch in range(n_epoches):
			# init loss & acc
			train_loss = 0
			train_acc = 0
			for step, (b_x, b_y) in enumerate(train_loader):		# gives batch data
				b_x = b_x.view(-1, self.n_features, self.time_steps)	# reshape x to (batch, n_features, time_step)
				if self.use_cuda == 1:
					b_x, b_y = Variable(b_x).cuda(), Variable(b_y).cuda()
				else:
					b_x, b_y = Variable(b_x), Variable(b_y)
				# get hidden
				self.m_cnnblstm_with_adabn.init_hidden(b_x.size(0))
				# update adabn running stats
				self.update_adabn_running_stats()
				# get output
				output = self(b_x)									# CNN_BLSTM output
				# get loss
				loss = loss_func(output, b_y)						# cross entropy loss
				train_loss += loss.item() * len(b_y)
				_, pre = torch.max(output, 1)
				num_acc = (pre == b_y).sum()
				train_acc += num_acc.item()
				# backward
				optimizer.zero_grad()								# clear gradients for this training step
				loss.backward()										# backpropagation, compute gradients
				optimizer.step()									# apply gradients

				# print loss
				print("[{}/{}], train loss is: {:.6f}, train acc is: {:.6f}".format(step, len(train_loader), train_loss / ((step + 1) * batch_size), train_acc / ((step + 1) * batch_size)))

			# save params
			self.save_params()

		print("train finish!")

	def getTestAccuracy(self, test_x, test_y):
		# init params
		self.init_partial_weights()

		# load params
		self.load_params()

		# set eval
		self.eval()

		with torch.no_grad():
			if self.use_cuda == 1:
				test_x, test_y = Variable(test_x).cuda(), Variable(test_y).cuda()
			else:
				test_x, test_y = Variable(test_x), Variable(test_y)
		# get hidden
		self.m_cnnblstm_with_adabn.init_hidden(test_x.size(0))
		# update adabn running stats
		self.update_adabn_running_stats()
		# get output
		output = self(test_x)
		print(output)
		prediction = torch.max(output, 1)[1]
		pred_y = prediction.data.numpy()
		print(pred_y)
		target_y = test_y.numpy()
		print(test_y)

		accuracy = float((pred_y == target_y).astype(int).sum()) / float(target_y.size)
		print("Accuracy: ", str(accuracy))

	def save_params(self):
		self.save_adabn_variables()
		torch.save(self.state_dict(), os.path.join(self.transfer_params_dir, cnnblstm_with_adabn.PARAMS_FILE))
		print("save_params success!")

	def save_adabn_variables(self):
		self.m_cnnblstm_with_adabn.net1_adabn.save_attrs()
		self.m_cnnblstm_with_adabn.net2_adabn.save_attrs()
		self.m_cnnblstm_with_adabn.net3_adabn.save_attrs()

	def load_params(self):
		self.load_adabn_variables()
		if os.path.exists(os.path.join(self.transfer_params_dir, cnnblstm_with_adabn.PARAMS_FILE)):
			if self.use_cuda == 0:
				self.load_state_dict(torch.load(os.path.join(self.transfer_params_dir, cnnblstm_with_adabn.PARAMS_FILE), map_location = torch.device('cpu')))
			else:
				self.load_state_dict(torch.load(os.path.join(self.transfer_params_dir, cnnblstm_with_adabn.PARAMS_FILE), map_location = torch.device('cuda')))
			print("load_params success!")

	def load_adabn_variables(self):
		self.m_cnnblstm_with_adabn.net1_adabn.load_attrs()
		self.m_cnnblstm_with_adabn.net2_adabn.load_attrs()
		self.m_cnnblstm_with_adabn.net3_adabn.load_attrs()

	def get_model(self, pre_trained = False):
		if pre_trained:
			self.load_params()
		return self

if __name__ == '__main__':
	use_cuda = torch.cuda.is_available()
	if use_cuda:
		cnnblstm = transfer_cnnblstm_with_adabn(use_cuda = 1).cuda()
	else:
		cnnblstm = transfer_cnnblstm_with_adabn(use_cuda = 0)
	print(cnnblstm)
	# get train_x, train_y
	train_x = torch.rand(20, 3, 800, dtype = torch.float32)
	train_y = torch.randint(10, (20, ), dtype = torch.int64)
	# train_y = torch.LongTensor(20, 1).random_() % 10
	print(train_x.type())
	# train_y = torch.zeros(20, 10).scatter_(1, train_y, 1)
	print(train_y)
	train_data = torch.utils.data.TensorDataset(train_x, train_y)
	cnnblstm.trainAllLayers(train_data)