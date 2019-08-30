import numpy as np
import pickle

def reverse_ld_coeffs(ld_law, q1, q2): 
    if ld_law == 'quadratic':
        coeff1 = 2.*np.sqrt(q1)*q2
        coeff2 = np.sqrt(q1)*(1.-2.*q2)
    elif ld_law=='squareroot':
        coeff1 = np.sqrt(q1)*(1.-2.*q2)
        coeff2 = 2.*np.sqrt(q1)*q2
    elif ld_law=='logarithmic':
        coeff1 = 1.-np.sqrt(q1)*q2
        coeff2 = 1.-np.sqrt(q1)
    elif ld_law == 'linear':
        return q1,q2
    return coeff1,coeff2

from scipy.stats import gamma,norm,beta,truncnorm
import numpy as np

def transform_uniform(x,hyperparameters):
    a,b = hyperparameters
    return a + (b-a)*x

def transform_loguniform(x,hyperparameters):
    a,b = hyperparameters
    la=np.log(a)
    lb=np.log(b)
    return np.exp(la + x*(lb-la))

def transform_normal(x,hyperparameters):
    mu,sigma = hyperparameters
    return norm.ppf(x,loc=mu,scale=sigma)

def transform_beta(x,hyperparameters):
    a,b = hyperparameters
    return beta.ppf(x,a,b)

def transform_exponential(x,hyperparameters):
    a = hyperparameters
    return gamma.ppf(x, a)

def transform_truncated_normal(x,hyperparameters):
    mu, sigma, a, b = hyperparameters
    ar, br = (a - mu) / sigma, (b - mu) / sigma
    return truncnorm.ppf(x,ar,br,loc=mu,scale=sigma)

def input_error_catcher(t,y,yerr,datatype):
    if datatype == 'lightcurve':
        dname = 'lc'
    else:
        dname = 'rv'
    if (y is None):
        raise Exception('INPUT ERROR: No '+datatype+' data was fed to juliet. \n'+\
                        ' Make sure to pass data (y_'+dname+') and errors (yerr_'+dname+').')
    if (yerr is None):
        raise Exception('INPUT ERROR: No ERRORS (yerr_'+dname+') on the '+datatype+' data were fed to juliet. \n'+\
                        ' Make sure to pass data (y_'+dname+') and errors (yerr_'+dname+')..')

def read_data(fname):
    fin = open(fname,'r')
    ts = np.array([])
    fs = np.array([])
    ferrs = np.array([])
    instruments = np.array([])
    # Arguments of an optional linear model. This will save the regression matrix "X" in a model of the form X*theta = y, where theta
    # are the coefficients:
    lm_arguments = {}
    # This will save a True or False for each instrument --- True if there are 
    # inputs and therefore we want a linear model, False if not:
    lm_boolean = {}
    instrument_names = []
    while True:
        line = fin.readline()
        if line != '':
            all_vals = line.split()
            t,f,ferr,instrument = all_vals[0:4]
            lm_variables = all_vals[4:]
            ts = np.append(ts,np.double(t))
            fs = np.append(fs,np.double(f))
            ferrs = np.append(ferrs,np.double(ferr))
            instruments = np.append(instruments,instrument.split()[0])
            if instrument.split()[0] not in instrument_names:
                instrument_names.append(instrument.split()[0])
                if len(lm_variables)>0:
                    lm_arguments[instrument.split()[0]] = np.array([])
                    lm_boolean[instrument.split()[0]] = True
                else:
                    lm_boolean[instrument.split()[0]] = False
            if lm_boolean[instrument.split()[0]]:
                if len(lm_arguments[instrument.split()[0]]) == 0:
                   lm_arguments[instrument.split()[0]] = np.array(lm_variables).astype(np.double)
                else:
                   lm_arguments[instrument.split()[0]] = np.vstack((lm_arguments[instrument.split()[0]],\
                                                              np.array(lm_variables).astype(np.double)))
        else:
            break
    # Identify instrument indeces:
    indexes = {}
    for instrument in instrument_names:
        indexes[instrument] = np.where(instruments == instrument)[0]
    return ts,fs,ferrs,instruments,indexes,len(instrument_names),instrument_names,lm_boolean,lm_arguments

def will_it_float(value):
    """
    Function name idea taken from https://stackoverflow.com/questions/736043/checking-if-a-string-can-be-converted-to-float-in-python.
    """
    try:
        float(value)
        return True
    except ValueError:
        return False
        
def readGPeparams(fname):
    fin = open(fname,'r')
    GPDictionary = {}
    ftime = True
    global_model = False
    while True:
        line = fin.readline()
        if line != '':
            if line[0] != '#':
                vector = line.split()
                variables,instrument = vector[:-1],vector[-1].split()[0]
                if ftime:
                    if will_it_float(instrument):
                        global_model = True
                        appended_vector = np.append(np.double(np.array(variables)),np.double(np.array(instrument)))
                    else:
                        global_model = False
                        appended_vector = np.double(np.array(variables))
                else:
                    if global_model:
                        appended_vector = np.append(np.double(np.array(variables)),np.double(np.array(instrument)))
                    else:
                        appended_vector = np.double(np.array(variables))
                    
                if global_model:
                    if ftime:
                        GPDictionary['global_model'] = appended_vector
                        ftime = False
                    else:
                        GPDictionary['global_model'] = np.vstack((GPDictionary['global_model'],appended_vector))
                else:
                    #variables,instrument = vector[:-1],vector[-1].split()[0]
                    if ftime:
                        ftime = False
                    if instrument in GPDictionary.keys():
                        GPDictionary[instrument] = np.vstack((GPDictionary[instrument],appended_vector))
                    else:
                        GPDictionary[instrument] = {}
                        GPDictionary[instrument] = appended_vector
        else:
            break
    return GPDictionary,global_model

def readpriors(priorname):
    """
    This function takes either a string or a dict and spits out information about the prior. If a string, it 
    reads a prior file. If a dict, it assumes the input dictionary has already defined all the variables and 
    distributions and simply spits out information about the system (e.g., number of transiting planets, RV 
    planets, etc.)
    """
    input_dict = False
    if type(priorname) == str:
        fin = open(priorname)
        priors = {}
    else:
        counter = -1
        priors = priorname
        input_dict = True
        all_parameters = priors.keys()
        n_allkeys = len(all_parameters)
    n_transit = 0
    n_rv = 0
    n_params = 0
    numbering_transit = np.array([])
    numbering_rv = np.array([])
    while True:
        if not input_dict:
            line = fin.readline()
        else:
            # Dummy variable so we enter the while:
            line = 'nc'
            counter += 1
        if line != '': 
            if line[0] != '#':
                if not input_dict:
                    out = line.split()
                    parameter,prior_name,vals = line.split()
                    parameter = parameter.split()[0]
                    # For retro-compatibility, if parameter is of the form sigma_w_rv_instrument change to
                    # sigma_w_instrument:
                    if parameter[:10] == 'sigma_w_rv':
                        instrument = parameter.split('_')[-1]
                        parameter = 'sigma_w_'+instrument
                    prior_name = prior_name.split()[0]
                    vals = vals.split()[0]
                    priors[parameter] = {}
                else:
                    param = all_parameters[counter]
                    parameter,prior_name = param,priors[param]['distribution']
                pvector = parameter.split('_')
                # Check if parameter/planet is from a transiting planet:
                if pvector[0] == 'r1' or pvector[0] == 'p':
                    pnumber = int(pvector[1][1:])
                    numbering_transit = np.append(numbering_transit,pnumber)
                    n_transit += 1
                # Check if parameter/planet is from a RV planet:
                if pvector[0] == 'K':
                    pnumber = int(pvector[1][1:])
                    numbering_rv = np.append(numbering_rv,pnumber)
                    n_rv += 1
                #if parameter == 'r1_p'+str(n_transit+1) or parameter == 'p_p'+str(n_transit+1):
                #    numbering_transit = np.append(numbering_transit,n_transit+1)
                #    n_transit += 1
                #if parameter == 'K_p'+str(n_rv+1):
                #    numbering_rv = np.append(numbering_rv,n_rv+1)
                #    n_rv += 1
                if prior_name.lower() == 'fixed':
                    if not input_dict:
                        priors[parameter]['distribution'] = prior_name.lower()
                        priors[parameter]['hyperparameters'] = np.double(vals)
                        priors[parameter]['cvalue'] = np.double(vals)
                else:
                    n_params += 1
                    if not input_dict:
                        priors[parameter]['distribution'] = prior_name.lower()
                        if priors[parameter]['distribution'] != 'truncatednormal':
                            v1,v2 = vals.split(',')
                            priors[parameter]['hyperparameters'] = [np.double(v1),np.double(v2)]
                        else:
                            v1,v2,v3,v4 = vals.split(',')
                            priors[parameter]['hyperparameters'] = [np.double(v1),np.double(v2),np.double(v3),np.double(v4)]
                        priors[parameter]['cvalue'] = 0.
        else:
            break
        if input_dict:
            if counter == n_allkeys-1:
                break
    if not input_dict:
        return priors,n_transit,n_rv,numbering_transit.astype('int'),numbering_rv.astype('int'),n_params
    else:
        return n_transit,n_rv,numbering_transit.astype('int'),numbering_rv.astype('int'),n_params

def get_phases(t,P,t0):
    """
    Given input times, a period (or posterior dist of periods)
    and time of transit center (or posterior), returns the 
    phase at each time t.
    """
    if type(t) is not float:
        phase = ((t - np.median(t0))/np.median(P)) % 1
        ii = np.where(phase>=0.5)[0]
        phase[ii] = phase[ii]-1.0
    else:
        phase = ((t - np.median(t0))/np.median(P)) % 1
        if phase>=0.5:
            phase = phase - 1.0
    return phase

def get_quantiles(dist,alpha = 0.68, method = 'median'):
    """
    get_quantiles function
    DESCRIPTION
        This function returns, in the default case, the parameter median and the error% 
        credibility around it. This assumes you give a non-ordered 
        distribution of parameters.
    OUTPUTS
        Median of the parameter,upper credibility bound, lower credibility bound
    """
    ordered_dist = dist[np.argsort(dist)]
    param = 0.0
    # Define the number of samples from posterior
    nsamples = len(dist)
    nsamples_at_each_side = int(nsamples*(alpha/2.)+1)
    if(method == 'median'):
       med_idx = 0
       if(nsamples%2 == 0.0): # Number of points is even
          med_idx_up = int(nsamples/2.)+1
          med_idx_down = med_idx_up-1
          param = (ordered_dist[med_idx_up]+ordered_dist[med_idx_down])/2.
          return param,ordered_dist[med_idx_up+nsamples_at_each_side],\
                 ordered_dist[med_idx_down-nsamples_at_each_side]
       else:
          med_idx = int(nsamples/2.)
          param = ordered_dist[med_idx]
          return param,ordered_dist[med_idx+nsamples_at_each_side],\
                 ordered_dist[med_idx-nsamples_at_each_side]

def bin_data(x,y,n_bin):
    x_bins = []
    y_bins = []
    y_err_bins = []
    for i in range(0,len(x),n_bin):
        x_bins.append(np.median(x[i:i+n_bin-1]))
        y_bins.append(np.median(y[i:i+n_bin-1]))
        y_err_bins.append(np.sqrt(np.var(y[i:i+n_bin-1]))/np.sqrt(len(y[i:i+n_bin-1])))
    return np.array(x_bins),np.array(y_bins),np.array(y_err_bins)

def writepp(fout,posteriors):
    if 'pu' in posteriors:
        pu = posteriors['pu']
        pl = posteriors['pl']
        Ar = (pu - pl)/(2. + pl + pu)

    fout.write('# {0:18} \t \t {1:12} \t \t {2:12} \t \t {3:12}\n'.format('Parameter Name','Median','Upper 68 CI','Lower 68 CI'))
    for pname in posteriors['posterior_samples'].keys():
      if pname != 'unnamed':
        val,valup,valdown = get_quantiles(posteriors['posterior_samples'][pname])
        usigma = valup-val
        dsigma = val - valdown
        fout.write('{0:18} \t \t {1:.10f} \t \t {2:.10f} \t \t {3:.10f}\n'.format(pname,val,usigma,dsigma))
        if pname.split('_')[0] == 'r2':
            par,planet = pname.split('_')
            r1 = posteriors['posterior_samples']['r1_'+planet]
            r2 = posteriors['posterior_samples']['r2_'+planet]
            b,p = np.zeros(len(r1)),np.zeros(len(r1))
            for i in range(len(r1)):
                if r1[i] > Ar:
                    b[i],p[i] = (1+pl)*(1. + (r1[i]-1.)/(1.-Ar)),\
                                (1-r2[i])*pl + r2[i]*pu
                else:
                    b[i],p[i] = (1. + pl) + np.sqrt(r1[i]/Ar)*r2[i]*(pu-pl),\
                                pu + (pl-pu)*np.sqrt(r1[i]/Ar)*(1.-r2[i])
            val,valup,valdown = get_quantiles(p)
            usigma = valup-val
            dsigma = val - valdown
            fout.write('{0:18} \t \t {1:.10f} \t \t {2:.10f} \t \t {3:.10f}\n'.format('p_'+planet,val,usigma,dsigma))
            val,valup,valdown = get_quantiles(b)
            usigma = valup-val
            dsigma = val - valdown
            fout.write('{0:18} \t \t {1:.10f} \t \t {2:.10f} \t \t {3:.10f}\n'.format('b_'+planet,val,usigma,dsigma))
            # Calculate inclination:
            if 'ecosomega_'+planet in posteriors['posterior_samples']:
                iplanet = planet[1:]
                ecc = np.sqrt(posteriors['posterior_samples']['ecosomega_p'+str(iplanet)]**2+posteriors['posterior_samples']['esinomega_p'+str(iplanet)]**2)
                omega = np.arctan2(posteriors['posterior_samples']['esinomega_p'+str(iplanet)],\
                               posteriors['posterior_samples']['ecosomega_p'+str(iplanet)])
            elif 'secosomega_'+planet in posteriors['posterior_samples']:
                iplanet = planet[1:]
                ecc = posteriors['posterior_samples']['secosomega_p'+str(iplanet)]**2+posteriors['posterior_samples']['sesinomega_p'+str(iplanet)]**2
                omega = np.arctan2(posteriors['posterior_samples']['sesinomega_p'+str(iplanet)],\
                                   posteriors['posterior_samples']['secosomega_p'+str(iplanet)])
            elif 'ecc_'+planet in posteriors['posterior_samples']:
                ecc = posteriors['posterior_samples']['ecc_'+planet]
                omega = posteriors['posterior_samples']['omega_'+planet]*np.pi/180.
            else:
                 ecc = 0.
                 omega = 90.
            ecc_factor = (1. + ecc*np.sin(omega))/(1. - ecc**2)
            if 'rho' in posteriors['posterior_samples']:
                G = 6.67408e-11
                a = ((posteriors['posterior_samples']['rho']*G*((posteriors['posterior_samples']['P_'+planet]*24.*3600.)**2))/(3.*np.pi))**(1./3.)
            else:
                a = posteriors['posterior_samples']['a_'+planet]
            inc_inv_factor = (b/a)*ecc_factor
            inc = np.arccos(inc_inv_factor)*180./np.pi
            val,valup,valdown = get_quantiles(inc)
            usigma = valup-val
            dsigma = val - valdown
            fout.write('{0:18} \t \t {1:.10f} \t \t {2:.10f} \t \t {3:.10f}\n'.format('inc_'+planet,val,usigma,dsigma))

        if pname.split('_')[0] == 'P':
            if 'rho' in posteriors['posterior_samples']:
                par,planet = pname.split('_')
                G = 6.67408e-11
                a = ((posteriors['posterior_samples']['rho']*G*((posteriors['posterior_samples']['P_'+planet]*24.*3600.)**2))/(3.*np.pi))**(1./3.)
                val,valup,valdown = get_quantiles(a)
                usigma = valup-val
                dsigma = val - valdown
                fout.write('{0:18} \t \t {1:.10f} \t \t {2:.10f} \t \t {3:.10f}\n'.format('a_'+planet,val,usigma,dsigma))
        if pname.split('_')[0] == 'ecosomega':
            par,planet = pname.split('_')
            iplanet = planet[1:]
            ecc = np.sqrt(posteriors['posterior_samples']['ecosomega_p'+str(iplanet)]**2+posteriors['posterior_samples']['esinomega_p'+str(iplanet)]**2)
            omega = np.arctan2(posteriors['posterior_samples']['esinomega_p'+str(iplanet)],\
                               posteriors['posterior_samples']['ecosomega_p'+str(iplanet)])*(180/np.pi)

            val,valup,valdown = get_quantiles(ecc)
            usigma = valup-val
            dsigma = val - valdown
            fout.write('{0:18} \t \t {1:.10f} \t \t {2:.10f} \t \t {3:.10f}\n'.format('ecc_'+planet,val,usigma,dsigma))

            idx = np.where(omega>0.)[0]
            val,valup,valdown = get_quantiles(omega[idx])
            usigma = valup-val
            dsigma = val - valdown
            fout.write('{0:18} \t \t {1:.10f} \t \t {2:.10f} \t \t {3:.10f}\n'.format('omega_'+planet,val,usigma,dsigma))

        if pname.split('_')[0] == 'secosomega':
            par,planet = pname.split('_')
            iplanet = planet[1:]
            ecc = posteriors['posterior_samples']['secosomega_p'+str(iplanet)]**2+posteriors['posterior_samples']['sesinomega_p'+str(iplanet)]**2
            omega = np.arctan2(posteriors['posterior_samples']['sesinomega_p'+str(iplanet)],\
                               posteriors['posterior_samples']['secosomega_p'+str(iplanet)])*(180/np.pi)

            val,valup,valdown = get_quantiles(ecc)
            usigma = valup-val
            dsigma = val - valdown
            fout.write('{0:18} \t \t {1:.10f} \t \t {2:.10f} \t \t {3:.10f}\n'.format('ecc_'+planet,val,usigma,dsigma))

            idx = np.where(omega>0.)[0]
            val,valup,valdown = get_quantiles(omega[idx])
            usigma = valup-val
            dsigma = val - valdown
            fout.write('{0:18} \t \t {1:.10f} \t \t {2:.10f} \t \t {3:.10f}\n'.format('omega_'+planet,val,usigma,dsigma))
    fout.close()

from astropy.time import Time as APYTime
def convert_time(conv_string,t):
    input_t,output_t = conv_string.split('->')
    if input_t != output_t:
        tobj = APYTime(t, format = 'jd', scale = input_t)
        # print('new_t = tobj.'+output_t+'.jd')
        # exec('new_t = tobj.'+output_t+'.jd')
        if output_t == 'utc':
            return tobj.utc.jd
        else:
            return t
        # return new_t
    else:
        return t