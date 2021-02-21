import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


class AI_Predictor():
	""" Instantiates our AI prediction tool. """
	def __init__(self):
		self.path     = "../redes_neuronales/data/datos_pulidos/"
		self.filename = "predictions.csv"

		self.energy_labels = ["eolica",
							  "nuclear",
							  "fuel",
							  "carbon",
							  "ciclo combinado",
                			  "hidraulica",
                			  "intercambios_int",
                			  "enlace_balear",
                			  "solar_foto",
                			  "solar_term",
                			  "term_renovable",
                			  "cogeneracion"]

		self.energy_estructura_labels = ["EÃ³lica",
										 "Nuclear",
										 "Fuel/gas",
										 "CarbÃ³n",
										 "Ciclo combinado",
                            			 "HidrÃ¡ulica",
                            			 "Intercambios int",
                            			 "Enlace balear",
                            			 "Solar fotovoltaica",
                            			 "Solar tÃ©rmica",
                            			 "TÃ©rmica renovable",
                            			 "CogeneraciÃ³n y residuos"]

		self.e_labels     = {e: self.energy_labels.index(e) for e in self.energy_labels}
		self.e_labels_inv = {v: k for k,v in self.e_labels.items()}
		self.exchange_labels = {l: e_l for l, e_l in zip(self.energy_labels, self.energy_estructura_labels)}

		# cargamos el csv con nuestras predicciones.
		self.preds = pd.read_csv(self.path+self.filename, sep=";")


		# Let's assign an eco-score to each t
		self.total_pred = np.sum(self.preds.values, axis=1)
		self.coeffs = {'eolica':           0.05,
				  'nuclear':          0.8,
				  'fuel':             0.673,
				  'carbon':           0.956, 
				  'ciclo combinado':  0.359, 
				  'hidraulica':       0.1, 
				  # 'intercambios_int': 6, 
				  # 'enlace_balear':    7, 
				  'solar_foto':       0.05, 
				  'solar_term':       0.05, 
				  'term_renovable':   0.125, 
				  'cogeneracion':     0.350}

		
        # Calculate both Abs and Rel Eco-Scores
		self.preds["eco_score_abs"] = self.absoluteScore()
		self.preds["eco_score_rel"]      = self.relativeScore(self.preds["eco_score_abs"])


	def absoluteScore(self):
		""" Calculates the Absolute Eco-score. """
		eco_score = []
		print("Calculating Absolute eco-score")
		for i, row in self.preds.iterrows():
			scores = 10 - 10*sum([self.coeffs[k] * (row[k]/self.total_pred[i]) for k in self.coeffs.keys()])
			# print(scores)
			eco_score.append(scores)
			# if i%10000 == 0:
			# 	print("Iteration:", i, "done")
				# break
		return eco_score

	def relativeScore(self, eco_score):
		""" Calculates the Absolute Eco-score. """
		eco_score_rel = []
		global_max, global_min = max(eco_score[1010:]), min(eco_score[1010:])
		# calculate each eco-score
		for i, score in enumerate(eco_score):
			# nonsense to rescale at i = 0
			if i == 0:
				eco_score_rel.append(5)
				continue
		    # escribimos el valor en referencia a los valores de las ultimas horas
			if i< 2*144:
				minimum = min(eco_score[:i])
				maximum = max(eco_score[:i])
			else:
				minimum = min(eco_score[i-2*144:i])
				maximum = max(eco_score[i-2*144:i])
		        
			minimum = ((minimum)+global_min)/2
			maximum = ((maximum)+global_max)/2
			# print(maximum, minimum)
			# si = (score - minimum) / (maximum-minimum)
			eco_score_rel.append( 10 * self.cap((score - minimum) / (maximum-minimum)) )
		    
		    # if i%10000 == 0:
		    #     print("Iteration:", i, "done")
		return eco_score_rel


	def cap(self, x, a=0, b=1):
		if x>b:
			return b
		elif x<a:
			return a
		else:
			return x

	def calculate(self, month, day, start_time, travel_time, charging_time=4):
		n = int((30*month + day)*144 + start_time*6 + travel_time*6)
		k = 25

		# print("Punto numero: ", n)
		rel_ = np.mean(self.preds["eco_score_rel"].values[n:n+charging_time])
		abs_ = np.mean(self.preds["eco_score_abs"].values[n:n+charging_time])

		# print("El eco_score_abs sociado es: ", abs_)
		# print("El eco_score_rel sociado es: ", rel_)

		# See if a better eco-score is available for the next 5 hours
		delta      = None
		delta_rel_ = None
		eco_score_plans = [np.mean(self.preds["eco_score_rel"].values[n+j:n+j+charging_time]) for j in range(k)]
		if max(eco_score_plans) > rel_: 
			delta 		= eco_score_plans.index(max(eco_score_plans))*10 # minutes till departure
			delta_rel_  = max(eco_score_plans) 
			# mostramos la opcion de mejora
			print("\n ////// ALERTA /////// \n")
			print("Si te esperas un poco conseguirás un mejor eco-score!")
			print("El eco-score planeado puede llegar a ser de: ", delta_rel_, "dentro de", delta, "minutos")

		return int(abs_*100)/100, int(rel_*100)/100, delta, int((abs_-rel_)*100)/100

	def genPlots(self, month, day, start_time, charging_time=4):
		n = int((30*month + day)*144 + start_time*6)
		k = 25+6*3
		# First generate the Eco-score plot
		eco_scores = [np.mean(self.preds["eco_score_rel"].values[n+j:n+j+charging_time]) 
						for j in range(k)]
		plt.figure()
		plt.plot(eco_scores, "g-")
		plt.legend(["Eco-Score"], loc="upper right")
		plt.savefig("static/img/eco_score.png")

		# Now generate the generation structure plot
		preds_mini = self.preds.iloc[n:n+k, :]
		preds_mini = preds_mini.drop(columns=['intercambios_int', 
											  'enlace_balear',
											  'eco_score_abs',
											  'eco_score_rel'])
		preds_mini.plot.area()
		plt.savefig("static/img/gen_struct.png")

		return

def scoreChargers(ai_predictor, month, day, start_time, first_chargers):
	""" Assigns a Score to each charger. """
	for i, charger in enumerate(first_chargers):
		travel_time = charger["eta"]
		abs_, rel_, delta, delta_rel_ = ai_predictor.calculate(month,
															   day,
															   start_time,
															   travel_time)
		first_chargers[i]["abs_"]       = abs_
		first_chargers[i]["rel_"]       = rel_
		first_chargers[i]["delta"]      = delta
		first_chargers[i]["delta_rel_"] = delta_rel_

	# generate the plots
	ai_predictor.genPlots(month, day, start_time)

	return first_chargers

