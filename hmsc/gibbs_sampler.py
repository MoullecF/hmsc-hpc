# MIT License

# Copyright (c) 2022 Kit Gallagher

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import numpy as np
import tensorflow as tf
import sys
from hmsc.updaters.updateEta import updateEta
from hmsc.updaters.updateAlpha import updateAlpha
from hmsc.updaters.updateBetaLambda import updateBetaLambda
from hmsc.updaters.updateLambdaPriors import updateLambdaPriors
from hmsc.updaters.updateNf import updateNf
from hmsc.updaters.updateGammaV import updateGammaV
from hmsc.updaters.updateSigma import updateSigma
from hmsc.updaters.updateZ import updateZ


class GibbsParameter:
    def __init__(self, value, conditional_posterior, posterior_params=None):
        self.__value = value
        self.conditional_posterior = conditional_posterior
        self.posterior_params = posterior_params

    def __str__(self) -> str:
        pass

    def __repr__(self) -> str:
        return str(self.__value)

    def get_value(self):
        return self.__value

    def set_value(self, value):
        self.__value = value

    value = property(get_value, set_value)

    def sample(self, sample_params):
        param_values = {}
        for k, v in sample_params.items():
            if isinstance(v, GibbsParameter):
                param_values[k] = v.value
            else:
                param_values[k] = v
        post_params = param_values
        self.__value = self.conditional_posterior(post_params)
        return self.__value


class GibbsSampler(tf.Module):
    def __init__(self, modelDims, modelData, priorHyperparams, rLHyperparams):

        self.modelDims = modelDims
        self.modelData = modelData
        self.priorHyperparams = priorHyperparams
        self.rLHyperparams = rLHyperparams

    @staticmethod
    def printFunction(i, samInd):
        outStr = "iteration " + str(i.numpy())
        if samInd.numpy() >= 0:
            outStr += " saving " + str(samInd.numpy())
        else:
            outStr += " transient"
        sys.stdout.write("\r" + outStr)

    @tf.function
    def sampling_routine(
        self,
        paramsTmp,
        num_samples=100,
        sample_burnin=0,
        sample_thining=1,
        verbose=1,
        print_retrace_flag=True,
    ):
        if print_retrace_flag:
            print("retracing")

        ns = self.modelDims["ns"]
        nc = self.modelDims["nc"]
        nr = self.modelDims["nr"]
        npVec = self.modelDims["np"]

        params = paramsTmp.copy()
        parNamesFix = ["Beta","Gamma","V","sigma"]
        parNamesRan = ["Lambda","Psi","Delta","Eta","Alpha"]
        
        # mcmcSamples = {}
        # for parName in parNamesFix:
        #   mcmcSamples[parName] = tf.TensorArray(params[parName].dtype, size=num_samples, name="mcmcSamples%s"%parName)
        # for parName in parNamesRan:
        #   mcmcSamples[parName] = [tf.TensorArray(params[parName][r].dtype, size=num_samples, name="mcmcSamples%s_%d"%(parName, r)) for r in range(nr)]          
        # print(mcmcSamples)
        
        mcmcSamplesBeta = tf.TensorArray(params["Beta"].dtype, size=num_samples)
        mcmcSamplesGamma = tf.TensorArray(params["Gamma"].dtype, size=num_samples)
        mcmcSamplesV = tf.TensorArray(params["V"].dtype, size=num_samples)
        mcmcSamplesSigma = tf.TensorArray(params["sigma"].dtype, size=num_samples)
        mcmcSamplesLambda = [tf.TensorArray(params["Lambda"][r].dtype, size=num_samples) for r in range(nr)]
        mcmcSamplesPsi = [tf.TensorArray(params["Psi"][r].dtype, size=num_samples) for r in range(nr)]
        mcmcSamplesDelta = [tf.TensorArray(params["Delta"][r].dtype, size=num_samples) for r in range(nr)]
        mcmcSamplesEta = [tf.TensorArray(params["Eta"][r].dtype, size=num_samples) for r in range(nr)]
        mcmcSamplesAlpha = [tf.TensorArray(params["Alpha"][r].dtype, size=num_samples) for r in range(nr)]

        
        step_num = sample_burnin + num_samples * sample_thining
        print("Iterations %d" % step_num)
        for n in tf.range(step_num):
            tf.autograph.experimental.set_loop_options(
                shape_invariants=[
                    (params["Eta"], [tf.TensorShape([npVec[r], None]) for r in range(nr)]),
                    (params["Beta"], tf.TensorShape([nc, ns])),
                    (params["Lambda"], [tf.TensorShape([None, ns])] * nr),
                    (params["Psi"], [tf.TensorShape([None, ns])] * nr),
                    (params["Delta"], [tf.TensorShape([None, 1])] * nr),
                    (params["Alpha"], [tf.TensorShape([None, 1])] * nr),
                ]
            )

            params["Z"] = updateZ(params, self.modelData)
            params["Beta"], params["Lambda"] = updateBetaLambda(params, self.modelData)
            params["Gamma"], params["V"] = updateGammaV(params, self.modelData, self.priorHyperparams)
            params["sigma"] = updateSigma(params, self.modelData, self.priorHyperparams)
            params["Psi"], params["Delta"] = updateLambdaPriors(params, self.rLHyperparams)
            params["Eta"] = updateEta(params, self.modelData, self.modelDims, self.rLHyperparams)
            params["Alpha"] = updateAlpha(params, self.rLHyperparams)
            
            if n < sample_burnin:
                params["Lambda"], params["Psi"], params["Delta"], params["Eta"] = updateNf(params, self.rLHyperparams, n)

            samInd = tf.cast((n - sample_burnin + 1) / sample_thining - 1, tf.int32)
            if (n + 1) % verbose == 0:
                tf.py_function(
                    func=GibbsSampler.printFunction, inp=[n, samInd], Tout=[]
                )
            if (n >= sample_burnin) & ((n - sample_burnin + 1) % sample_thining == 0):                
                # for parName in parNamesFix:
                #   mcmcSamples[parName] = mcmcSamples[parName].write(samInd, params[parName])
                # for parName in parNamesRan:
                #   for r in range(nr):
                #     mcmcSamples[parName][r] = mcmcSamples[parName][r].write(samInd, params[parName][r])
                mcmcSamplesBeta = mcmcSamplesBeta.write(samInd, params["Beta"])
                mcmcSamplesGamma = mcmcSamplesGamma.write(samInd, params["Gamma"])
                mcmcSamplesV = mcmcSamplesV.write(samInd, params["V"])
                mcmcSamplesSigma = mcmcSamplesSigma.write(samInd, params["sigma"])
                mcmcSamplesLambda = [mcmcSamples.write(samInd, par) for mcmcSamples, par in zip(mcmcSamplesLambda, params["Lambda"])]
                mcmcSamplesPsi = [mcmcSamples.write(samInd, par) for mcmcSamples, par in zip(mcmcSamplesPsi, params["Psi"])]
                mcmcSamplesDelta = [mcmcSamples.write(samInd, par) for mcmcSamples, par in zip(mcmcSamplesDelta, params["Delta"])]
                mcmcSamplesEta = [mcmcSamples.write(samInd, par) for mcmcSamples, par in zip(mcmcSamplesEta, params["Eta"])]
                mcmcSamplesAlpha = [mcmcSamples.write(samInd, par) for mcmcSamples, par in zip(mcmcSamplesAlpha, params["Alpha"])]


        print("Completed iterations %d" % step_num)
        samples = {}
        # for parName in parNamesFix:
        #   samples[parName] = mcmcSamples[parName].stack()
        # for parName in parNamesRan:
        #   samples[parName] = [None] * nr
        #   for r in range(nr):
        #     mcmcSamples[parName][r] = mcmcSamples[parName][r].stack()
        samples["Beta"] = mcmcSamplesBeta.stack()
        samples["Gamma"] = mcmcSamplesGamma.stack()
        samples["V"] = mcmcSamplesV.stack()
        samples["sigma"] = mcmcSamplesSigma.stack()
        samples["Lambda"] = [mcmcSamples.stack() for mcmcSamples in mcmcSamplesLambda]
        samples["Psi"] = [mcmcSamples.stack() for mcmcSamples in mcmcSamplesPsi]
        samples["Delta"] = [mcmcSamples.stack() for mcmcSamples in mcmcSamplesDelta]
        samples["Eta"] = [mcmcSamples.stack() for mcmcSamples in mcmcSamplesEta]
        samples["Alpha"] = [mcmcSamples.stack() for mcmcSamples in mcmcSamplesAlpha]

        return samples
