import ujson as json
import os


def load_model_from_json(json_file_path):

    with open(json_file_path) as json_file:
        hmsc_obj = json.load(json_file)

    return hmsc_obj, hmsc_obj.get("hM")


def save_postList_to_json(postList, postList_file_path, chain):

    print("Start dumping.")

    json_data = {}

    for i in range(len(postList)):
        sample_data = {}
        params = postList[i]
        
        sample_data["Beta"] = params["Beta"].numpy().tolist()
        sample_data["Gamma"] = params["Gamma"].numpy().tolist()
        sample_data["V"] = params["V"].numpy().tolist()
        sample_data["rhoInd"] = (params["rhoInd"]+1).numpy().tolist()
        sample_data["sigma"] = params["sigma"].numpy().tolist()
        
        sample_data["Lambda"] = [par.numpy().tolist() for par in params["Lambda"]]
        sample_data["Psi"] = [par.numpy().tolist() for par in params["Psi"]]
        sample_data["Delta"] = [par.numpy().tolist() for par in params["Delta"]]
        sample_data["Eta"] = [par.numpy().tolist() for par in params["Eta"]]
        sample_data["Alpha"] = [par.numpy().tolist() for par in params["Alpha"]]

        sample_data["wRRR"] = sample_data["rho"] = sample_data["PsiRRR"] = sample_data["DeltaRRR"] = None
        json_data[i] = sample_data

    postList_file_path = (
        os.path.splitext(postList_file_path)[0] + "_" + str(chain+1) + ".json"
    )
    print("Dumping, chain %d" % chain)
    with open(postList_file_path, "w") as fp:
        json.dump(json_data, fp)


def save_chains_postList_to_json(postList, postList_file_path, nChains):

    json_data = {chain: {} for chain in range(nChains)}

    for chain in range(nChains):
        for i in range(len(postList[chain])):
            sample_data = {}
            params = postList[chain][i]

            sample_data["Beta"] = params["Beta"].numpy().tolist()
            sample_data["Gamma"] = params["Gamma"].numpy().tolist()
            sample_data["V"] = params["V"].numpy().tolist()
            sample_data["rhoInd"] = (params["rhoInd"]+1).numpy().tolist()
            sample_data["sigma"] = params["sigma"].numpy().tolist()
            
            sample_data["Lambda"] = [par.numpy().tolist() for par in params["Lambda"]]
            sample_data["Psi"] = [par.numpy().tolist() for par in params["Psi"]]
            sample_data["Delta"] = [par.numpy().tolist() for par in params["Delta"]]
            sample_data["Eta"] = [par.numpy().tolist() for par in params["Eta"]]
            sample_data["Alpha"] = [par.numpy().tolist() for par in params["Alpha"]]
            
            sample_data["wRRR"] = sample_data["rho"] = sample_data["PsiRRR"] = sample_data["DeltaRRR"] = None

            json_data[chain][i] = sample_data

    with open(postList_file_path, "w") as fp:
        json.dump(json_data, fp)
