__all__ = ['GP_sampling_square_exp', 'GP_sampling_exp', 'GP_sampling_concentrated', 'k_SPDE_construct']

import scipy.sparse as ss
import scipy.sparse.linalg as sla
import numpy as np
import scipy.sparse as ss
from scipy.sparse.linalg import spsolve
import seaborn as sns
import matplotlib.pyplot as plt

# ------------------------ part 1: training data construction for GP case ------------------------

def GP_sampling_square_exp(x, cl, num):
    'description'
    # function for sampling the Gaussian Process of square exponential kernel

    MC_samples = []
    rng = np.random.RandomState(14)
    
    # define the kernel of sample paths
    def cov(xs, ys, l, sigma=1):
    # Pairwise difference matrix.
        dx = np.expand_dims(xs, 1) - np.expand_dims(ys, 0)
        return (sigma ** 2) * np.exp(-((dx / l) ** 2) / 2)
    
    # define the mean of the sample paths
    def m(xs):
        return np.zeros_like(xs)
    
    mean = m(xs=x)
    cov = cov(xs=x, ys=x, l=cl, sigma=1)
    for k in range(num):
        data = rng.multivariate_normal(mean, cov)   # generate the samples
        MC_samples.append(data)
    MC_samples = np.array(MC_samples)

    return MC_samples



def GP_sampling_exp(x, cl, num):
    'description'
    # function for sampling the Gaussian Process of exponential kernel

    MC_samples = []
    rng = np.random.RandomState(14)
    
    # define the kernel of sample paths
    def cov(xs, ys, l, sigma=1):
    # Pairwise difference matrix.
        dx = np.abs(np.expand_dims(xs, 1) - np.expand_dims(ys, 0))
        return (sigma ** 2) * np.exp(-(dx / l))
    
    # define the mean of the sample paths
    def m(xs):
        return np.zeros_like(xs)
    
    mean = m(xs=x)
    cov = cov(xs=x, ys=x, l=cl, sigma=1)
    for k in range(num):
        data = rng.multivariate_normal(mean, cov)   # generate the samples
        MC_samples.append(data)
    MC_samples = np.array(MC_samples)

    return MC_samples

def GP_sampling_concentrated(x, cl, num):
    'description'
    # function for sampling the Gaussian Process of square exponential kernel which is 
    # conentrated on the boundary of the spatial doamin

    MC_samples = []
    rng = np.random.RandomState(14)
    
    # define the kernel of sample paths
    def cov(xs, ys, l, sigma=1):
    # Pairwise difference matrix.
        dx = np.expand_dims(xs, 1) - np.expand_dims(ys, 0)
        return (sigma ** 2) * np.exp(-((dx / l) ** 2) / 2)
    
    # define the mean of the sample paths
    def m(xs):
        return np.zeros_like(xs)
    
    mean = m(xs=x)
    cov = cov(xs=x, ys=x, l=cl, sigma=1)
    for k in range(num):
        data = rng.multivariate_normal(mean, cov)   # generate the samples
        data = (1-x*x) * data
        MC_samples.append(data)
    MC_samples = np.array(MC_samples)

    return MC_samples

# ------------------------ part 2: training data construction for SDE case ------------------------

class SDE():
    def __init__(self, mesh_size):
        super(SDE, self).__init__()
        self.mesh_size = mesh_size

    def khat_k(self, xs, ys, l):      # khat(x) kernel function
        dx = np.expand_dims(xs, 1) - np.expand_dims(ys, 0)
        return (4/25) * np.exp(-((dx/l) ** 2))

    def khat_m(self, x):          # khat(x) mean function
        return np.zeros_like(x)

    def k_Y(self, k_X, khat_Y):    # calculate the function value of coefficient term
        k_Y = np.exp(0.2 * np.sin(1.5 * np.pi * (k_X+1)) + khat_Y)
        return k_Y

    def f_k(self, xs, ys, a, sigma, l):    # f(x) kernel function
        dx = np.expand_dims(xs, 1) - np.expand_dims(ys, 0)
        return (sigma ** 2) * (9/400) * np.exp(- ((dx / l) ** 2) / (a ** 2))

    def f_m(self, x):             # f(x) mean function
        return np.zeros_like(x) + 0.5

    def u_solve(self, k, f):
        h = 2/self.mesh_size            # step
        
        # construct matrix A using second order approximation
        diag_up = (np.roll(k,-1) + 4*k - np.roll(k,1))[1:-2]
        diag_down = (np.roll(k,1) + 4*k - np.roll(k,-1))[2:-1]
        diag = -8 * k[1:-1]
        A = ss.csr_matrix(np.diag(diag) + np.diag(diag_up,1) + np.diag(diag_down,-1))
        
        # construct RHS b
        f = f[1:-1]
        b = - 40 * (h**2) * f
        
        # solve the system
        u = sla.spsolve(A,b)
        zero = np.array([0])
        u = np.concatenate((zero,u,zero),axis=0)
        return u

    def forward(self, Num, kL, fL, a):
        k_samples = []
        f_samples = []
        u_samples = []
        
        rng = np.random.RandomState(10)           # define a random state
        x = np.linspace(-1, 1, self.mesh_size+1)  # construct the coordinate of x：401 points uniformly distributed on [-1,1]
        
        # construct corresponding mean function and covariance matrix of the stoachastic process
        mean_k = self.khat_m(x)
        cov_k = self.khat_k(x,x,l=kL)
        mean_f = self.f_m(x)
        cov_f = self.f_k(x,x,a=a,sigma=1,l=fL)
        
        Yk = rng.multivariate_normal(mean_k, cov_k, Num)
        Yf = rng.multivariate_normal(mean_f, cov_f, Num)
        
        # construct the sample paths of f(x) and k(x) (limited number: 300 or 1000 or 3000)
        for i in range(Num):
            k = self.k_Y(x,Yk[i])
            f = Yf[i]       # sensor data
            u = self.u_solve(k, f)
            k_samples.append(k)
            f_samples.append(f)
            u_samples.append(u)
        
        k_samples = np.array(k_samples)
        f_samples = np.array(f_samples)
        u_samples = np.array(u_samples)

        return k_samples, f_samples, u_samples

##可视化采样路径
def samples_plot(data, flag_sensor):
    plt.fig, ax = plt.subplots()
    x = np.linspace(-1, 1, len(data[0, :]))
    sensor_position = np.linspace(-1, 1, flag_sensor)
    lower_bound = np.min(np.min(np.array(data)))
    upper_bound = np.max(np.max(np.array(data)))
    for i in range(20):
        ax.plot(x, data[i, :], linewidth = 1)
        # for k in range(flag_sensor):
        #     plt.vlines(sensor_position[k], lower_bound, upper_bound, colors="k", linestyles="dashed")
    plt.grid(True, axis='x', linestyle='solid')
    # plt.axis('off')
    # plt.gcf().set_size_inches(512 / 100, 512 / 100)
    # plt.gca().xaxis.set_major_locator(plt.NullLocator())
    # plt.gca().yaxis.set_major_locator(plt.NullLocator())
    # plt.subplots_adjust(top=1, bottom=0, right=0.93, left=0, hspace=0, wspace=0)
    # plt.margins(0, 0)

    plt.savefig(f'f_sample_0.08.eps', bbox_inches='tight', dpi=300)
    plt.show()

# --------------------- part 3: construct the training data if directly runned ----------------------

if __name__ == "__main__":

    # convey the parameters from command line
    import argparse
    parser = argparse.ArgumentParser(description='manual to this script')
    parser.add_argument('--case', type=str, default = 'ODE')
    parser.add_argument('--mesh_size', type=int, default = 100)
    parser.add_argument('--data_size', type=int, default = 1000)
    args = parser.parse_args()

    # if set information for each case
    Case = args.case
    if Case == 'ODE':
        lengthscale_k = 1.0
        lengthscale_f = 0.2
        a = 1.0
    if Case == 'ODE_high':
        lengthscale_k = 1.0
        lengthscale_f = 0.2
        a = 0.02 or 0.08

    mesh_size = args.mesh_size
    dataset_size = args.data_size

    if Case == 'ODE' or 'ODE_khigh' or 'ODE_fhigh' or 'ODE_kfhigh':
        SDE_data = SDE(mesh_size=args.mesh_size)
        k_samples, f_samples, u_samples = SDE_data.forward(args.data_size, kL=1.0, fL=0.2, a=0.08)
        samples_plot(f_samples, 21)
        # np.save(file=r'../database/SDE/u_0.02_ref.npy', arr=u_samples)
        # np.save(file=r'../database/SDE/k_0.02_ref.npy', arr=k_samples)
        # np.save(file=r'../database/SDE/f_0.02_ref.npy', arr=f_samples)

    