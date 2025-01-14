import gym, numpy as np
from utils import *
from methods import *
from true_online_GTD import TRUE_ONLINE_GTD_LEARNER
from VARIABLE_LAMBDA import LAMBDA

def MTA(env, episodes, target, behavior, evaluate, Lambda, encoder, learner_type = 'togtd', gamma = lambda x: 0.95, alpha = 0.05, beta = 0.05, kappa = 0.01):
    value_trace = np.empty((episodes, 1)); value_trace[:] = np.nan
    if learner_type == 'togtd':
        MC_exp_learner, L_exp_learner, L_var_learner, value_learner = TRUE_ONLINE_GTD_LEARNER(env), TRUE_ONLINE_GTD_LEARNER(env), TRUE_ONLINE_GTD_LEARNER(env), TRUE_ONLINE_GTD_LEARNER(env)
    else:
        pass # not implemented, should try TD
    for episode in range(episodes):
        o_curr, done = env.reset(), False
        x_curr = encoder(o_curr)
        log_rho_accu = 0 # use log accumulation of importance sampling ratio to increase stability
        MC_exp_learner.refresh(); L_exp_learner.refresh(); L_var_learner.refresh(); value_learner.refresh()
        value_trace[episode, 0] = evaluate(value_learner.w_curr, 'expectation')
        while not done:
            action = decide(o_curr, behavior)
            rho_curr = importance_sampling_ratio(target, behavior, o_curr, action)
            log_rho_accu = log_rho_accu + np.log(target[o_curr, action]) - np.log(behavior[o_curr, action])
            o_next, R_next, done, _ = env.step(action)
            x_next = encoder(o_next)
            # learn expectation of MC-return!
            MC_exp_learner.learn(R_next, gamma(x_next), gamma(x_curr), x_next, x_curr, 1.0, 1.0, rho_curr, alpha, beta)
            # learn expectation of \Lambda-return!
            L_exp_learner.learn(R_next, gamma(x_next), gamma(x_curr), x_next, x_curr, Lambda.value(x_next), Lambda.value(x_curr), rho_curr, 1.1 * alpha, 1.1 * beta)
            # learn variance of \Lambda-return!
            delta_curr = R_next + gamma(x_next) * np.dot(x_next, value_learner.w_curr) - np.dot(x_curr, value_learner.w_curr)
            try:
                r_bar_next = delta_curr ** 2
            except RuntimeWarning:
                pass
            gamma_bar_next = (Lambda.value(x_next) * gamma(x_next)) ** 2
            L_var_learner.learn(r_bar_next, gamma_bar_next, 1, x_next, x_curr, 1, 1, rho_curr, alpha, beta)
            # SGD on meta-objective
            if np.exp(log_rho_accu) > 1e6: break # too much, not trustworthy
            v_next = np.dot(x_next, value_learner.w_curr)
            var_L_next, exp_L_next, exp_MC_next = np.dot(x_next, L_var_learner.w_curr), np.dot(x_next, L_exp_learner.w_curr), np.dot(x_next, MC_exp_learner.w_curr)
            coefficient = gamma(x_next) ** 2 * Lambda.value(x_next) * ((v_next - exp_L_next) ** 2 + var_L_next) + v_next * (exp_L_next + exp_MC_next) - v_next ** 2 - exp_L_next * exp_MC_next
            Lambda.gradient_descent(x_next, kappa * np.exp(log_rho_accu) * coefficient)
            # learn value
            value_learner.learn(R_next, gamma(x_next), gamma(x_curr), x_next, x_curr, Lambda.value(x_next), Lambda.value(x_curr), rho_curr, alpha, beta)
            MC_exp_learner.next(); L_exp_learner.next(); L_var_learner.next(); value_learner.next()
            o_curr, x_curr = o_next, x_next
    return value_trace

def eval_MTA_per_run(env, runtime, runtimes, episodes, target, behavior, kappa, gamma, Lambda, alpha, beta, evaluate, encoder, learner_type):
    print('running %d of %d for MTA' % (runtime + 1, runtimes))
    value_trace = MTA(env, episodes, target, behavior, evaluate, Lambda, encoder, learner_type = 'togtd', gamma = gamma, alpha = alpha, beta = beta, kappa = kappa)
    return (value_trace, None)

def eval_MTA(env, expectation, variance, stat_dist, behavior, target, kappa, gamma, alpha, beta, runtimes, episodes, evaluate):
    LAMBDAS = []
    for runtime in range(runtimes):
        LAMBDAS.append(LAMBDA(env, np.ones(env.observation_space.n), approximator = 'linear'))
    results = Parallel(n_jobs = -1)(delayed(eval_MTA_per_run)(env, runtime, runtimes, episodes, target, behavior, kappa, gamma, LAMBDAS[runtime], alpha, beta, evaluate, lambda s: onehot(s, env.observation_space.n), 'togtd') for runtime in range(runtimes))
    value_traces = [entry[0] for entry in results]
    if evaluate is None:
        error_value = np.zeros((runtimes, episodes))
        for runtime in range(runtimes):
            w_trace = value_traces[runtime]
            for j in range(len(w_trace)):
                error_value[runtime, j] = mse(w_trace[j], expectation, stat_dist)
        return error_value
    else:#
        return np.concatenate(value_traces, axis = 1).T