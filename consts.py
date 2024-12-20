import numpy as np
inputs = 91

#need everywhere
# max_to_mass = 265625 #kg
mf = 0.39 #is best here
m_OE = 0.5#0.50 #<- values are better

#class I initial
R_nominal = 11716 #[km
R_diversion = 250 #[km]
t_E = 45 #[min]
f_con = 0
# m_OE = 0.65
M_pl = 8500 #design payload! [kg]
M_pl_max = 18960

c_L_cruise = 0.52924 #from the cruise angle of attack section
parasite_drag = 0.0075

#matching diagram
approach_speed = 78 
landing_massfraction = 0.79
landing_temp_diff = 15
landing_fieldlengthreq = 1981.2

cruise_massfraction = 0.95
cruise_altitude = 9449.8
cruise_pressure = 101325*(1+(-0.0065* cruise_altitude/288.15))**(-9.81/(-0.0065*287))
ref_altitude = 100
cruise_temp = 288.15-0.0065*(cruise_altitude-ref_altitude)
cruise_minmach = 0.85
cruise_speed = 0.85 * np.sqrt(1.4*287*cruise_temp)

climb_req = 5 #roughly 1000ft/min (really small lmao but at 0.95 the mtow?)
climb_altitude = 7400

to_massfraction = 0.85
to_altitude = 7400
to_cL = 2.036181377 #to be changed?
to_field_length = 3048
to_oswald_efficiency = 0.8286
to_temp = 298
to_pressure = 95457.84253

wetted_ratio = 6
friction_coefficient = 0.0028
parasite_drag = 0.0075
span_efficiency = 0.97

climbgradient_massfraction = [1, 1, 1, 1, 0.79]
climbgradient_zerodrag = [0.0758, 0.0563, 0.0363, 0.0168, 0.0558] # taken from drag polar D:38-
climbgradient_gradient = [3.2, 0 , 0, 1.2, 2.1]
climbgradient_oswaldfactor = [0.867622569, 0.828622569, 0.828622569, 0.789622569, 0.867622569]

#SAR
specific_fuel_energy = 44e6

#efficiencies
efficiency_tf = 0.75

#powerplant
#PW PW1000G
bypass_ratio = 11 #change to 11
S_wnac = 50 #[m^2] #change to 50
jet_eff = ((cruise_speed)/(22*np.power(bypass_ratio, -0.19)))/specific_fuel_energy * 1000000
M_powerplant = 5000*2 #total weight; change 10000
nacelle_diameter = 2.5
nacelle_length = 4.37

# #Some other option
# bypass_ratio = 10
# S_wnac = 100 #[m^2]
# jet_eff = ((cruise_speed)/(22*np.power(bypass_ratio, -0.19)))/specific_fuel_energy * 1000000
# M_powerplant = 15000 #total weight;
# nacelle_diameter = 4
# nacelle_length = 5.5

## HLDs and Control Surfaces
sweep_quarter = np.radians(28.39)
taper_ratio = 0.2*(2-sweep_quarter)
hld_margin = 1

#airfoil
Clratio =  0.8  #1.04
Clmax = 1.797
CLmax_wingclean = Clratio * Clmax
t_cratio = 0.12
#C_L design
clmax_landing = 2.6 

delta_c_to_cf = 0.64
c_ratio_TE = 1+ 0.35 * delta_c_to_cf #single-slotted fowler flap trailing edge
delta_clmax = 1.3 * c_ratio_TE #single-slotted fowler 
C_lalpha = 6.7614
c_ratio_LE = 1.1 #slat at the leading edge
cl_leadingedge = 0.4*c_ratio_LE
C_d0wing = 0.0008 #wing 

P = np.radians(20)
stall_speed = 69.44
dalpha = 0.4581

tau = 0.4

#empennage
htail_sweep = 38 #deg
htail_AR = 4
htail_taper_ratio = 1/2

vtail_sweep = 40 #deg
vtail_AR = 3/2
vtail_taper_ratio = 1/2

sumart = """                                                     
 __
 \\  \\     _ _                ,---------------------------,
  \\**\\ ___\\/ \\...............| this thing make plane lol |
X*#####*+~~\\_\\               `---------------------------'
  o/\\  \\
     \\__\\"""

