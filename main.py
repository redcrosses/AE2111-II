import numpy as np
from consts import *
from fuselage import *
import math
import matplotlib.pyplot as plt
from intersect import intersection
import inspect
from unit_conversion import *
from Class_II_weight import *
import sympy as sp
from scipy.optimize import minimize_scalar

###FUNCTIONS AND CLASSES##
wing_loading = np.arange(0.1,9100,100) #<- 0.1 avoids the division by zero warning
#class I
def Class_1_est(liftoverdrag,h_CR,V_CR,jet_eff,energy_fuel,R_nom, R_div,t_E, f_con, m_OE, M_pl, override = False):
	# energy fuel is like the weird 41sth/kw or idk
	#t_E is the Loiter time in emergencies
	g=9.81
	R_lost = 1/0.7 * (liftoverdrag) * (h_CR + (V_CR**2)/(2*g)) /1000 # lost range via : LIft/Drag , height of cruise, velocity cruise
	R_eq = (R_nom + R_lost)*(1+f_con)+1.2 * R_div + (t_E * V_CR *60/1000)
	# nominal and lost range plus fraction trip fuel for contingency
	if override:
		m_f= 0.415 #0.4 #<- iteration breaks but initial values are better
	else:
		m_f = 1- np.exp((-R_eq * g * 1000)/(jet_eff * energy_fuel * liftoverdrag))
		
	M_MTO = M_pl /(1-(m_OE)-(m_f))  # m_OE taken from reference or hallucinated
	M_f = m_f * M_MTO
	M_OE= m_OE * M_MTO
	print(R_lost, R_eq, R_div, m_f)
	print("\n\033[1m\033[4m Class I Weight Estimation \033[0m")
	print("{:24} {:f} {:16}\n{:24} {:f} {:16}\n{:24} {:f} {:16}\n{:24} {:f} {:16}".format("Operating empty:", M_OE, "[kg]", "Fuel:", M_f, "[kg]", "Max TO:", M_MTO, "[kg]", "Fuel mass fraction:", m_f, ""))
	return(M_OE, M_f, M_MTO, m_f) #in kilos small m is mass fraction, big M is acutal mass

#matching diagram
def min_speed_list(clmax_landing):
	landing_airdensity = 101325/(287*( landing_temp_diff+288.15))
	return  clmax_landing*(( approach_speed/1.23)**2)*landing_airdensity/(2* landing_massfraction)

def field_length_list(clmax_landing):
	landing_airdensity = 101325/(287*( landing_temp_diff+288.15))
	return 1/ landing_massfraction* landing_fieldlengthreq/0.45*landing_airdensity* clmax_landing/2

def cruise_speed_list():
	cruise_pressure = 101325*(1+(-0.0065* cruise_altitude/288.15))**(-9.81/(-0.0065*287))
	cruise_totalpressure = cruise_pressure*(1+(1.4-1)/2* cruise_minmach**2)**3.5
	cruise_deltapressure = cruise_totalpressure/101325
	cruise_thrustlapse = cruise_deltapressure*(1-(0.43+0.014* bypass_ratio)*math.sqrt( cruise_minmach))
	zerolift_drag =  friction_coefficient* wetted_ratio
	oswald_efficiency = 1/(math.pi* aspect_ratio* parasite_drag+(1/ span_efficiency))
	cruise_density = cruise_pressure/(287* cruise_temp)
	cruise_speed = math.sqrt(1.4*287* cruise_temp)* cruise_minmach
	return  cruise_massfraction/cruise_thrustlapse*((zerolift_drag*0.5*cruise_density*cruise_speed**2)/( cruise_massfraction*wing_loading)+( cruise_massfraction*wing_loading)/(math.pi* aspect_ratio*oswald_efficiency*0.5*cruise_speed**2*cruise_density))

class climb_gradient():
	def __init__(self, num):
		self.num=num

	def climb_gradient_list(self):
		climbgradient_maxcl = math.sqrt( climbgradient_zerodrag[self.num]*math.pi* bypass_ratio* climbgradient_oswaldfactor[self.num])
		climbgradient_best_speed = np.sqrt((wing_loading*2)/(1.225*climbgradient_maxcl))
		climbgradient_mach_number = climbgradient_best_speed/np.sqrt(1.4*287*288.15)
		climbgradient_total_pressure = (1+(1.4-1)/2*np.power(climbgradient_mach_number,2))*101325
		climbgradient_delta_pressure = climbgradient_total_pressure/101325
		climbgradient_thrust_lapse = climbgradient_delta_pressure*(1-(0.43+0.014* bypass_ratio)*np.sqrt(climbgradient_mach_number))
		# oswald_efficiency = 1/(math.pi* aspect_ratio* parasite_drag+(1/ span_efficiency))
		return 2* climbgradient_massfraction[self.num]/climbgradient_thrust_lapse*( climbgradient_gradient[self.num]/100+2*math.sqrt( climbgradient_zerodrag[self.num]/(math.pi* climbgradient_oswaldfactor[self.num]* bypass_ratio)))

def to_field_length_list(aspect_ratio):
	to_pressure = 101325*(1+(500*-0.0065)/(288.15))**(-9.81/(-0.0065*287))
	to_density = to_pressure/(287* to_temp)
	to_velocity = np.sqrt((9000*2)/(to_density* to_cL))
	to_mach_number = to_velocity/np.sqrt(1.4*287* to_temp)
	to_total_pressure = (1+(1.4-1)/2*np.power(to_mach_number,2))* to_pressure
	to_delta_pressure = to_total_pressure/101325
	to_thrust_lapse = to_delta_pressure*(1-(0.43+0.014* bypass_ratio)*np.sqrt(to_mach_number))
	return (1.15*to_thrust_lapse*np.sqrt(2 * wing_loading/( to_field_length * 0.85 * to_density * 9.81 * math.pi *  to_oswald_efficiency * aspect_ratio))+ 2*(4*11)/ to_field_length)

def find_design_point(target_pos, lines_arr):
	target = lines_arr[target_pos]
	intersections = []
	yvals = []
	for line in lines_arr[2:]: #first two lines are removed from the intersection; first one is itself and second one is parallel
		intrsctn = intersection(target[0],target[1],line[0],line[1])
		intersections.append(intrsctn)
		yvals.append(intrsctn[1])
	return intersections[yvals.index(max(yvals))] #return the point in the intersections list that has the maximum y-value of the intersection.

#Class II
def find_cg(fuselage_length, nose_cone_length, cabin_length, m_fuel):
	#LEMAC calculation
	xc_oew = 0.25
	M_empennage = 0.017
	M_fuselage = 0.101
	M_equipment = 0.089
	M_wing = 0.122
	M_Nacelle = 0.0056
	M_Prop = 0.0225
	fuselage_group = np.array([[M_empennage, M_fuselage, M_equipment],[0.9*fuselage_length, 0.4*fuselage_length, 0.4*fuselage_length]])
	wing_group = np.array([[M_wing, M_Nacelle, M_Prop],[0.4*MAC, -3, -3]])
	fus_sum = fuselage_group.prod(axis=0).sum()
	wing_sum = wing_group.prod(axis=0).sum()
	M_fus_sum = fuselage_group[0].sum()
	M_wing_sum = wing_group[0].sum()
	fus_pos = fus_sum/M_fus_sum
	wing_pos = wing_sum/M_wing_sum
	print(fus_pos, wing_pos)
	X_LEMAC = fus_pos + MAC*(wing_pos/MAC * M_wing_sum/M_fus_sum - xc_oew*(1+M_wing_sum/M_fus_sum))
	X_TEMAC = X_LEMAC + MAC
	#CG location
	m_Payload = 18960/max_to_mass
	cg_matrix = np.array([[m_OE, m_Payload, m_fuel],[X_LEMAC + xc_oew*MAC, nose_cone_length + 0.5*cabin_length, X_LEMAC+0.4*MAC]])
	moments = cg_matrix.prod(axis=0)
	print(moments)
	cg_positions = np.array([[cg_matrix[1][0], cg_matrix[0][0]],
				 [(moments[0]+moments[1])/(cg_matrix[0][0]+cg_matrix[0][1]),(cg_matrix[0][0]+cg_matrix[0][1])],
				 [(moments[0]+moments[1]+moments[2])/(cg_matrix[0][0]+cg_matrix[0][1]+cg_matrix[0][2]),(cg_matrix[0][0]+cg_matrix[0][1]+cg_matrix[0][2])],
				 [(moments[0]+moments[2])/(cg_matrix[0][0]+cg_matrix[0][2]),(cg_matrix[0][0]+cg_matrix[0][2])]]) #OEW, WOE+WP, WOE+WP+WF, WOE+WF
	# print(cg_positions)
	#plotting the cgs
	a,b = zip(*np.vstack([cg_positions,[cg_matrix[1][0], cg_matrix[0][0]]])) #added the starting point for proper plotting
	plt.subplot(223)
	plt.title("Cg Positions")
	plt.xlabel("x-position [m]")
	plt.ylabel("Mass fraction")
	plt.plot(a,b, 'bo-')
	plt.plot((X_LEMAC, X_TEMAC),(1,1),'ro-')
	plt.ylim(0,1.1)
	print("\n\033[1m\033[4m Cg Locations & Mass Fractions \033[0m")
	print("{:24} {:16}\n{:24} {:16}\n{:24} {:16}\n{:24} {:16}".format(
    "OEW:", ' [m], '.join(["{:.5f}".format(round(x, 5)) for x in cg_positions[0]]), 
    "WOE+WP:", ' [m], '.join(["{:.5f}".format(round(x, 5)) for x in cg_positions[1]]), 
    "WOE+WP+WF:", ' [m], '.join(["{:.5f}".format(round(x, 5)) for x in cg_positions[2]]), 
    "WOE+WF:", ' [m], '.join(["{:.5f}".format(round(x, 5)) for x in cg_positions[3]]))) #thanks gpt
	return cg_positions

def empennage_size(l_fus, cg_aft, l_MAC, S_wing, b):
	htail_aero_centre_location = l_fus - 4
	htail_moment_arm_cg_aft = htail_aero_centre_location - cg_aft 
	htail_c_v = 0.95
	htail_area = (htail_c_v * l_MAC * S_wing) / (htail_moment_arm_cg_aft)

	vtail_aero_centre_location = htail_aero_centre_location - 2
	vtail_moment_arm_cg_aft = vtail_aero_centre_location - cg_aft
	vtail_c_v = 0.066
	vtail_area = (vtail_c_v * b * S_wing) / (vtail_moment_arm_cg_aft)
	print("\n\033[1m\033[4m Empennage \033[0m")
	print("{:24} {:.5f} {:16}\n{:24} {:.5f} {:16}\n{:24} {:.5f} {:16}\n{:24} {:.5f} {:16}".format("Hor.Tail Location:", htail_aero_centre_location, "[m]", "Hor.Tail Area:", htail_area, "[m^2]", "Ver.Tail Location:", vtail_aero_centre_location, "[m]", "Ver.Tail Area:", vtail_area, "[m^2]"))
	return htail_aero_centre_location, htail_area, vtail_aero_centre_location, vtail_area

#dashboard diagrams
def weight_range( mu_j , liftoverdrag, e_f , M_MTO , M_pl , M_plMax , M_OE, R_nominal , h_CR , V_CR , R_div):
    g=9.81
    R_lost = 1 / 0.7 * (liftoverdrag) * (h_CR + (V_CR ** 2) / (2 * g)) / 1000
    R_aux= (R_nominal + R_lost)+1.2 * R_div + (t_E * V_CR *60/1000)  - R_nominal
    R_maxstruct= mu_j *(liftoverdrag) * (e_f / (g*1000)) * np.log((M_MTO)/(M_OE+M_plMax))-R_aux
    R_ferry= mu_j *(liftoverdrag) * (e_f / (g*1000)) * np.log((M_OE+M_f)/(M_OE))-R_aux
    # print(R_maxstruct); print(R_nominal); print(R_ferry)
    plt.subplot(221)
    plt.title("Payload-Range Diagram")
    plt.xlabel("Range [m]")
    plt.ylabel("Mass [kg]")
    #plt.plot([R_maxstruct ,M_plMax ],[R_nominal, M_pl],[R_ferry , 0])
    plt.plot([R_maxstruct, R_nominal , R_ferry],[M_plMax, M_pl , 0])
    plt.plot([0, 9545, 11716, 12697],[M_plMax,M_plMax, M_pl , 0])
def matchingdiag_print(lines, labels, design_point):
	plt.subplot(222)
	plt.title("Matching Diagram")
	plt.xlabel("W/S")
	plt.ylabel("T/W")
	for i in range(len(lines)): #plotting all lines
		plt.plot(lines[i][0], lines[i][1], label = labels[i])
	plt.plot(design_point[0], design_point[1],"ro")
	plt.gca().set_aspect('auto','box')
	plt.ylim(0,1)
	plt.legend()
	plt.grid()
def planform_print(span, root_c, tip_c,sweep_quart):
	plt.subplot(224)
	plt.title("Wing Planform")
	x = [0,0,span, span,0]
	y = [root_c, 0, 0.25*root_c + np.tan(sweep_quart)*span - 0.25*tip_c, 0.25*root_c + np.tan(sweep_quart)*span + 0.75*tip_c,root_c]
	plt.plot(x,y, 'ro-')
	plt.gca().set_aspect('equal', 'box')
	#ALSO MAKE IT PRINT THE FUSELAGE DIMENSIONS!

def aspect_rat(sweep_le,lower_bound, upper_bound):
    x = sp.symbols('x')
    # Define the function
    def y_func(x_val):
        return 1 / (sp.pi * x_val * (4.61 * (1 - 0.045 * x_val**0.68) * (sp.cos(sweep_le)**0.15) - 3.1))

    # Convert the function to a numerical form
    y_numeric = sp.lambdify(x, y_func(x), 'numpy')
    # Use minimize_scalar to find the minimum within the given bounds
    result = minimize_scalar(y_numeric, bounds=(lower_bound, upper_bound), method='bounded')
    return result.x  # return the x value

def cd0_FUNCTION(l_fus, l_wing):
	M=0.85
	rho=0.441653
	V=256.5793
	f_n=0.2763 ####nacelle length 0.9m and outer diameter 3.257
	l_nacelle=0.9
	mu=0.0000148881
	d=3.7328
	Re_wing = (rho * V * l_wing) / mu
	Re_fuselage = (rho * V * l_fus) / mu
	Re_nacelle=(rho * V * l_nacelle) / mu

	# Friction coefficients for wing
	Cf_laminar_wing = 1.328 / math.sqrt(Re_wing)
	Cf_turbulent_wing = 0.455 / (math.log10(Re_wing) ** 2.58 * (1 + 0.144 * M ** 2) ** 0.65)
	Cf_wing = 0.1 * Cf_laminar_wing + 0.9 * Cf_turbulent_wing

	# Friction coefficients for fuselage
	Cf_laminar_fuselage = 1.328 / math.sqrt(Re_fuselage)
	Cf_turbulent_fuselage = 0.455 / (math.log10(Re_fuselage) ** 2.58 * (1 + 0.144 * M ** 2) ** 0.65)
	Cf_fuselage = 0.05 * Cf_laminar_fuselage + 0.95 * Cf_turbulent_fuselage
	Cf_nacelle = 1.328 / math.sqrt(Re_nacelle)

	# Form factor for wing
	x_c = 0.126
	t_c = 0.12 * math.cos(math.radians(31.35))  # t/c with leading edge sweep ΛMAC = 17.45°
	FF_wing = (1 + 0.6 * (x_c / t_c) + 100 * (t_c) ** 4) * (1.34 * M ** 0.18 * (math.cos(math.radians(17.45))) ** 0.28)
	f=l_fus/d
	FF_wing = (1 + (0.6 / x_c) * t_c + 100 * (t_c) ** 4) * (1.34 * M ** 0.18 * math.cos(29.9) ** 0.28)
	FF_fuselage = (1 + 60 / (f ** 3) + f / 400)
	FF_nacelle=1+0.035/f_n
	return(Cf_fuselage*FF_fuselage,Cf_wing*FF_wing*1.1,Cf_nacelle*FF_nacelle*1.5)


def optimisation(clmax_landing, max_to_mass, c_d0initial):
	#matching diagram
	x_const = [100*i for i in range(0,91)]
 
	global lines, labels, design_point
	lines = [([min_speed_list(clmax_landing)]*91, x_const), ([field_length_list(clmax_landing)]*91, x_const),(wing_loading, cruise_speed_list())]
	labels = ["Minimum speed","Landing Field Length","Cruise speed","Climb Gradient 1","Climb Gradient 2","Climb Gradient 3","Climb Gradient 4","Climb Gradient 5","Takeoff Field Length"]

	gradient = climb_gradient(0)
	lines.append((wing_loading, 0.5*gradient.climb_gradient_list()))
	for i in range(1,5):
		gradient = climb_gradient(i)
		lines.append((wing_loading, gradient.climb_gradient_list()))
	lines.append((wing_loading, to_field_length_list(aspect_ratio)))

	design_point = find_design_point(0,lines) #make minimum speed line the target line to intersect with
	thrust_max = float(design_point[1][0])*max_to_mass*9.81 /1000

	##HLDs and Control surfaces 
	S =  max_to_mass*9.81 / float(design_point[0][0]) #<- column and row position avoids deprecation warning

	#wing parameters calculated from wing area
	span = np.sqrt(aspect_ratio*S)
	chord_root = 2*S / ((1+ taper_ratio)*span)
	chord_tip = chord_root *  taper_ratio
	y_1 = 0.10*span/2 #position of the beginning of the HLD; 15% of the half-span

	#sweep angle relations (probably should be a function lol)
	global sweep_LE, sweep_sixc, sweep_half
	sweep_LE = np.tan(sweep_quarter) + 0.25 * (2*chord_root)/(span)*(1-taper_ratio)
	sweep_sixc = np.tan(sweep_LE) - 0.6 * (2*chord_root)/(span)*(1-taper_ratio)
	sweep_half = np.tan(sweep_LE) - 0.5 * (2*chord_root)/(span)*(1-taper_ratio)
	#will need out of loop and this is easier
	global t_r, cruise_oswald_efficiency
	t_r = chord_root*t_cratio
	cruise_oswald_efficiency = 2/(2-aspect_ratio+np.sqrt(4+aspect_ratio**2 * (1+np.tan(sweep_half)**28)))#4.61*(1-0.045*np.power(aspect_ratio,0.68))*np.power(math.cos(sweep_quarter),0.15) - 3.1

		
	#HLD and Control surfaces placement
	delta_CLmax =  clmax_landing - cl_leadingedge -  CLmax_wingclean

	S_ratio = delta_CLmax/(0.9 *  delta_clmax * np.cos(sweep_sixc))

	S_wf = S_ratio * S
	y_2 = np.min(np.roots([-(chord_root - chord_tip)/(span), chord_root, ((chord_root - chord_tip)/(span) * np.power(y_1,2) - chord_root*y_1 - S_wf/2)])) +  hld_margin

	inter = 2* (chord_root - chord_tip)/span
	C_lp = -4 * ( C_lalpha +  C_d0wing)/(S * np.power(span,2)) * ((chord_root/3 * np.power(span/2,3) - inter * np.power(span/2,4)/4))

	C_lda = -( P * C_lp)/( dalpha) * (span/(2* stall_speed))
	b_2 = np.roots([2/3 * (chord_root - chord_tip)/span, -chord_root/2, 0, chord_root/2 * np.power(y_2, 2) - 2/3 * (chord_root - chord_tip)/span * np.power(y_2, 3) + (C_lda*S*span)/(2* C_lalpha* tau)])


	cruise_density = (101325*(1+(-0.0065* cruise_altitude/288.15))**(-9.81/(-0.0065*287))) /(287* cruise_temp)
	cruise_velocity =  cruise_minmach*np.sqrt(1.4* cruise_temp*287)
	c_Drag =  c_d0initial + np.power(c_L_cruise,2)/(np.pi*aspect_ratio*cruise_oswald_efficiency)
	Drag = c_Drag * 0.5*cruise_density*np.power(cruise_velocity,2) * S

	SAR =  specific_fuel_energy* efficiency_tf/(Drag)
	frame = inspect.currentframe()
	name,_,_,argvalue = inspect.getargvalues(frame)
	iteratedvalue = argvalue[name[0]]

	diff = span/2 - b_2[1]
	# print("\nS: %.5f [m^2] \nSpan: %.5f [m] \nRoot Chord: %.5f [m] \nTip Chord: %.5f [m] \ny_1: %.5f [m] \nHLD margin: %.5f" % (S, span, chord_root,  chord_tip, y_1,  hld_margin))
	# print("y_2 for HLD:", y_2)
	# print("b_2 for alieron (select the reasonable one):",b_2)
	# print("SAR:",SAR)
	# print(name[0], iteratedvalue)
	# print("Diff:", diff)
	return SAR, iteratedvalue, S, span, chord_root, chord_tip, S_wf, y_1, y_2, b_2[1], thrust_max, diff

def runthatshit(c_d0initial, run):
	######################################################
	#class 1 weight estimation
	global aspect_ratio,M_OE, M_f, M_MTO, m_f,labels,MAC
	aspect_ratio = aspect_rat(sweep_quarter+np.radians(2),0.1,15) #calculating the optimal aspect ratio of the wing given (leading edge) sweep
	initial_oswald = 2/(2-aspect_ratio+np.sqrt(4+aspect_ratio**2 * (1+np.tan(sweep_quarter)**28)))#4.61*(1-0.045*np.power(aspect_ratio,0.68))*np.power(math.cos(sweep_quarter),0.15) - 3.1 #1/(np.pi*aspect_ratio*parasite_drag + (1/0.97))
	liftoverdrag = 0.5*np.sqrt((np.pi*aspect_ratio*initial_oswald)/c_d0)
	print("LIFT OVER DRAG:",liftoverdrag)
 
	if run==1: override = True
	else: override = False #makes the fuel mass fraction 0.4 on the first run, then it is calculated
 
	M_OE, M_f, M_MTO, m_f = Class_1_est(liftoverdrag, cruise_altitude, cruise_speed, jet_eff, specific_fuel_energy, R_nominal, R_diversion, t_E, f_con, m_OE, M_pl, override)

	weight_range(jet_eff, liftoverdrag, specific_fuel_energy, M_MTO, M_pl , M_pl_max, M_OE , R_nominal , cruise_altitude , cruise_speed , R_diversion)
	#iterating the design (matching diagram, wing sizing, hld and control surfaces)
	results = []
	diffs = []
	current = 1000
	iterator = 10
	previous = [0]
	while True: #iterating the design
		var = current/1000
		run_tuple = optimisation(var, M_MTO, c_d0initial) #<-- optimisation function call
		run = list(run_tuple) 
		diffs.append(run[-1])
		results.append(run[:-1])
		current += iterator
	
		if(run[-1]<0 and previous[-1]>0): #this optimization ensures the hld and alierons fill the whole wing. Optimal SAR is only optimal if aspect ratio is optimal!
			optimal_list = previous
			optimalSAR,iterated_value,S_optimal,span,chord_root,chord_tip,S_wf,y_1,y_2,b_2,T_max,diff = previous_tuple
			matchingdiag_print(lines, labels, design_point)
			break
		elif(run[-1]>0 and previous[-1]<0):
			optimal_list = run
			optimalSAR,iterated_value,S_optimal,span,chord_root,chord_tip,S_wf,y_1,y_2,b_2,T_max,diff = run_tuple
			matchingdiag_print(lines, labels, design_point)
			break
		else:
			previous = run
			previous_tuple = run_tuple
	# print(SARs)
	#optimal result
	# optimaldiff = min(diffs) #optimal is found when the SAR is maximum in the iterated range
	# optimal = results[diffs.index(optimaldiff)] #print the optimal results based on optimal aspect ratio

	labels = [["Optimal SAR:",'Iterated value:', 'S:', 'Span:', 'Chord_root:', 'Chord_tip:', 'S_wf:','y_1 (HLD):', 'y_2 (HLD):', 'b_2 (Aileron):', 'Maximum Thrust:', 'Diff:'],["[m/kg]", "","[m^2]", "[m]","[m]","[m]","[m^2]","[m]","[m]","[m]",'[kN]','[m]']]
	print("\n\033[1m\033[4m Optimal Results [m] \033[0m")
	print("Iterated variable: {:>18}".format(optimisation.__code__.co_varnames[0]))
	print("{:24} {:.5f} {:16}".format("Aspect ratio:",aspect_ratio,""))
	for i in range(len(optimal_list)):
		print("{:24} {:.5f} {:16}".format(labels[0][i],optimal_list[i],labels[1][i]))
	planform_print(span/2,chord_root,chord_tip, sweep_quarter)

	#mean aerodynamic chord
	MAC = 2/3 * chord_root * ((1+taper_ratio+taper_ratio**2)/(1+taper_ratio))
	#finding the fuselage dimensions
	S_wfuselage, l_fuselage, l_cabin, l_ncone,w = fuselage(83.1) #THIS NEEDS TO BE DYNAMIC -- IT BREAKS FOR FUEL VOLUMES TOO SMALL output: fuselage wetted surface area, fuselage length, cabin length, nose cone length
	cg_positions = find_cg(float(l_fuselage), l_ncone, l_cabin,m_f)
	cg_aft = np.max(cg_positions[:,0])
	x_htail, htail_area, x_vtail, vtail_area = empennage_size(l_fuselage, cg_aft, MAC,S_optimal,span)

	#new drag estimation (fast estimation)
	S_wwing = 1.07 * 2 * S_optimal
	S_wHT = 1.05 * 2 * htail_area
	S_wVT = 1.05 * 2 * vtail_area
	S_wnacelles = 1 #todo
	cdc_fuselage, cdc_wing, cdc_nacelle = cd0_FUNCTION(l_fuselage, chord_root)
	c_d0new = 1.15 * (1/S_optimal * (S_wfuselage*cdc_fuselage + S_wwing*cdc_wing + S_wnacelles*cdc_nacelle + S_wHT*0.008 + S_wVT * 0.008))
	print("\nOLD c_d0: {0}, NEW c_d0: {1}".format(c_d0initial, c_d0new))
	print("\nOLD e: {0}, NEW e: {1}".format(initial_oswald, cruise_oswald_efficiency))

	W_fw = 0.5 * M_f  
	q = 0.5 * (cruise_pressure/(287* cruise_temp)) * cruise_speed**2
	N_z =3.75
	W_dg = M_MTO #Gross design weight
	L_t = 29.39 - 13.09 #Wing quarter mac to tail quarter mac # DONT TRUST THIS VALUE

	def g(x):
		value = (2*(x**2) - w**2) / (2*(x**2))
		# Ensure the value is within the valid range for arccos
		value = np.clip(value, -1, 1)
		return np.pi * (x**2) - (1/2) * (x**2) * (np.arccos(value) - np.sin(np.arccos(value)))

	# V_pr = g(3.12653) * l_cabin * 1.2 #inner diameter of cabin = constant = 3.12653 #1.2 to account for pressurized parts thats not cabin(complete guess)
	# p_delta = 45.6 * 10**3
	# W_press = 11.9 + (convert_units(V_pr, 'm^3', False) +convert_units(p_delta, 'pascals', False))**0.271
	# H_t_H_v = 0 #IDK
	# Nl = 1.5 * 3 # 1.5 * 3 wheels
	# Wl = M_MTO * 0.87 # 1.5 * 12 wheels
	# Lm = 6 #main landing gear length
	# Ln = 6 #nose landing gear length


	# Class_II_weight = class_II_weight(S_optimal, W_fw, aspect_ratio , sweep_quarter , q, taper_ratio , t_cratio , N_z, W_dg , S_wfuselage, L_t, liftoverdrag , W_press, htail_area , htail_sweep , htail_taper_ratio , vtail_area , vtail_sweep , H_t_H_v, vtail_taper_ratio , Nl, Wl, Lm, Ln)
	# work in progress!!
	return c_d0new

c_d0 = 0.0168#from Fred's excel Drag polar section
runcount = 1
while 69:
	plt.close()
	plt.figure(figsize=(20,20))
	print("RUN #{0}".format(runcount))
	c_d0 = runthatshit(c_d0,runcount)
	
	inp = input("Next run?")
	if inp=="show": plt.show()
	runcount+=1
	