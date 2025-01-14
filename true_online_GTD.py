import numpy as np
from joblib import Parallel, delayed
from utils import onehot, decide, importance_sampling_ratio, mse


class TRUE_ONLINE_GTD_LEARNER():
    def __init__(self, env):
        self.observation_space, self.action_space = env.observation_space, env.action_space
        self.w_curr, self.w_prev = np.zeros(self.observation_space.n), np.zeros(self.observation_space.n)
        self.h_curr, self.h_prev = np.zeros(self.observation_space.n), np.zeros(self.observation_space.n)
        self.refresh()

    def learn(self, R_next, gamma_next, gamma_curr, x_next, x_curr, lambda_next, lambda_curr, rho_curr, alpha_curr, beta_curr):
        self.rho_curr = rho_curr
        self.w_next, self.e_curr, self.e_grad_curr, self.e_h_curr, self.h_next = \
            self.true_online_gtd_step(R_next, gamma_next, gamma_curr, x_next, x_curr, self.w_curr, self.w_prev,
         lambda_next, lambda_curr, self.rho_curr, self.rho_prev,
         self.e_prev, self.e_grad_prev, self.e_h_prev, self.h_curr,
         alpha_curr, beta_curr)
        pass
        
    def next(self):
        self.w_curr, self.w_prev = np.copy(self.w_next), np.copy(self.w_curr)
        self.e_prev, self.e_grad_prev, self.e_h_prev = np.copy(self.e_curr), np.copy(self.e_grad_curr), np.copy(self.e_h_curr)
        self.h_curr, self.h_prev = np.copy(self.h_next), np.copy(self.h_curr)
        self.rho_prev = np.copy(self.rho_curr)
        del self.w_next, self.e_curr, self.e_grad_curr, self.e_h_curr, self.h_next, self.rho_curr

    def refresh(self):
        self.e_curr, self.e_prev = np.zeros(self.observation_space.n), np.zeros(self.observation_space.n)
        self.e_grad_curr, self.e_grad_prev = np.zeros(self.observation_space.n), np.zeros(self.observation_space.n)
        self.e_h_curr, self.e_h_prev = np.zeros(self.observation_space.n), np.zeros(self.observation_space.n)
        self.rho_prev = 1

    @staticmethod
    def true_online_gtd_step(R_next, gamma_next, gamma_curr, x_next, x_curr, w_curr, w_prev, lambda_next, lambda_curr, rho_curr, rho_prev, e_prev, e_grad_prev, e_h_prev, h_curr, alpha_curr, beta_curr):
        delta_curr = R_next + gamma_next * np.dot(x_next, w_curr) - np.dot(x_curr, w_curr)
        e_curr = rho_curr * (gamma_curr * lambda_curr * e_prev + alpha_curr * (1 - rho_curr * gamma_curr * lambda_curr * np.dot(x_curr, e_prev)) * x_curr)
        e_grad_curr = rho_curr * (gamma_curr * lambda_curr * e_grad_prev + x_curr)
        e_h_curr = rho_prev * gamma_curr * lambda_curr * e_h_prev + beta_curr * (1 - rho_prev * gamma_curr * lambda_curr * np.dot(x_curr, e_h_prev)) * x_curr
        w_next = w_curr + delta_curr * e_curr + (np.dot(w_curr, x_curr) - np.dot(w_prev, x_curr)) * (e_curr - alpha_curr * rho_curr * x_curr) - alpha_curr * gamma_next * (1 - lambda_next) * np.dot(h_curr, e_grad_curr) * x_next
        h_next = h_curr + rho_curr * delta_curr * e_h_curr - beta_curr * np.dot(x_curr, h_curr) * x_curr
        return w_next, e_curr, e_grad_curr, e_h_curr, h_next

def true_online_gtd(env, episodes, target, behavior, Lambda, gamma = lambda x: 0.95, alpha = 0.05, beta = 0.0001, diagnose = False, evaluate = None):
    """
    episodes:   number of episodes
    target:     target policy matrix (|S|*|A|)
    behavior:   behavior policy matrix (|S|*|A|)
    Lambda:     LAMBDA object determining each lambda for each feature (or state or observation)
    gamma:      anonymous function determining each lambda for each feature (or state or observation)
    alpha:      learning rate for the weight vector of the values
    beta:       learning rate for the auxiliary vector for off-policy
    """
    learner = TRUE_ONLINE_GTD_LEARNER(env)
    if evaluate is not None:
        value_trace = np.zeros((episodes, 1)); value_trace[:] = np.nan
    else:
        value_trace = []
    for epi in range(episodes):
        s_curr, done = env.reset(), False
        x_curr = onehot(s_curr, env.observation_space.n)
        learner.refresh()
        if evaluate is not None:
            value_trace[epi, 0] = evaluate(learner.w_curr, 'expectation')
        else:
            value_trace.append(np.copy(learner.w_curr))
        while not done:
            action = decide(s_curr, behavior)
            rho_curr = importance_sampling_ratio(target, behavior, s_curr, action)
            s_next, r_next, done, _ = env.step(action)
            x_next = onehot(s_next, env.observation_space.n)
            if diagnose:
                print('rho_curr: %.2e, lambda_curr: %.2e, lambda_next: %.2e' % (rho_curr, Lambda.value(x_curr), Lambda.value(x_next)))
            learner.learn(r_next, gamma(x_next), gamma(x_curr), x_next, x_curr, Lambda.value(x_next), Lambda.value(x_curr), rho_curr, alpha, beta)
            learner.next()
            x_curr = x_next
    return value_trace

def eval_togtd_per_run(env, truth, stat_dist, runtime, runtimes, episodes, target, behavior, gamma, Lambda, alpha, beta, evaluate):
    print('running %d of %d for togtd' % (runtime + 1, runtimes))
    value_trace = true_online_gtd(env, episodes, target, behavior, Lambda, gamma = gamma, alpha = alpha, beta = beta, evaluate = evaluate)
    if evaluate is not None:
        return value_trace.T
    else:
        result = np.zeros((1, episodes))
        for j in range(len(value_trace)):
            result[0, j] = mse(value_trace[j], truth, stat_dist)
        return result

def eval_togtd(env, truth, stat_dist, behavior, target, Lambda, gamma = lambda x: 0.95, alpha = 0.05, beta = 0.0001, runtimes=20, episodes=100000, evaluate=None):
    results = Parallel(n_jobs = -1)(delayed(eval_togtd_per_run)(env, truth, stat_dist, runtime, runtimes, episodes, target, behavior, gamma, Lambda, alpha, beta, evaluate) for runtime in range(runtimes))
    results = np.concatenate(results, axis=0)
    return results