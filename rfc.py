###############################################################################
#
#    Spirent TestCenter RFC2544 Test using Python
#             by Spirent Communications
#
# Date: May 15 2023
# Author: Sai Kiran Meduri - kiran.meduri@spirent.com
#
# Description: This is a rfc2544 test which uses predefined config tcc file, updates 
#              devices configs and run the sequencer. It will also generate results report 
#			   using Testcenter IQ custom template. 

"""
     Spirent TestCenter RFC2544 Testing
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    1.2 : 05/02/2023 - Sai Kiran Meduri
            -Added support for reading and updating multiple device from the configs for the port. 
            
    1.1 : 05/02/2023 - Sai Kiran Meduri
            -Added support for configuring ipv6, reading multiple ports from the config file. 

    1.0 : 04/14/2023 - Sai Kiran Meduri 
            -Released code to Cisco.
            
"""
###############################################################################
import time, json, os, sys
from time import sleep
from datetime import datetime
from stcrestclient.stcpythonrest import StcPythonRest as StcPython

stc = StcPython()

with open('config.json') as file:
    testdata = json.load(file)

def ipv4deviceconfig(testdata):
    global ports
    ports = stc.get("system1.project", "children-port")
    portslist = ports.split()

    for port in portslist:
        print('Port location:', stc.get(port, "location"))
        devices = stc.get(port, "AffiliationPort-Sources").split()
        devicelist = devices
        for i, device in enumerate(devicelist):
            configlocation = port+"device"+str((int(i)+1))+"ipv4config"
            print("Configuring: ", configlocation)
            ipconfig = stc.get(device, "children-Ipv4If")
            currentipconfig = stc.get(ipconfig, "Address", "Gateway","PrefixLength")    
            print("PRE-CONFIGURATION: ", currentipconfig)
            stc.config(ipconfig, Address=testdata[configlocation]["Address"],Gateway=testdata[configlocation]["Gateway"], PrefixLength=testdata[configlocation]["Prefix"]) 
            updateipconfig = stc.get(ipconfig, "Address", "Gateway","PrefixLength")
            print("POST-CONFIGURATION: ", updateipconfig, "\n")


def ipv6deviceconfig(testdata):    
    global ports
    ports = stc.get("system1.project", "children-port")
    portslist = ports.split()
    print(portslist)

    for port in portslist:
        print('Port location:', stc.get(port, "location"))
        devices = stc.get(port, "AffiliationPort-Sources").split()
        devicelist = devices
        for i, device in enumerate(devicelist):
            configlocation = port+"device"+str((int(i)+1))+"ipv6config"
            porthandle =[]
            for addr in stc.get(device, "children-Ipv6If").split():
                porthandle.append(addr)
            
            print("Configuring: ", configlocation)    
            currentipconfig = stc.get(porthandle[0], "Address", "Gateway","PrefixLength")
            print("PRE-CONFIGURATION: ", currentipconfig)
            stc.config(porthandle[0], Address=testdata[configlocation]["Address"],Gateway=testdata[configlocation]["Gateway"], PrefixLength=testdata[configlocation]["Prefix"]) 
            updateipconfig = stc.get(porthandle[0], "Address", "Gateway","PrefixLength")
            print("POST-CONFIGURATION: ", updateipconfig, "\n")

def runtest(testdata):  
    print('Reserving Ports and Applying Configuration')
    stc.perform("AttachPorts", AutoConnect="true", PortList=stc.get("system1.project", "children-port"))
    stc.apply()
    print('Config Applied Successfully')

    print('Starting ARP')
    stc.perform("ArpNdStartOnAllDevicesCommand")
    time.sleep(5)
    arpstatus()
    
    print('Running Command Sequencer')
    stc.perform("SequencerStart") 
    stc.waitUntilComplete() 
    print('seq done')
    
    stc.perform("StopEnhancedResultsTest")
    
def arpstatus():
    arp = stc.perform("ArpNdStartOnAllDevicesCommand") 
    status = arp["ArpNdState"]
    print("ARP Status: ", status)
    if status != "SUCCESSFUL":
        print("ARP FAILED, TERMINATING")
        stc.perform("terminatebll", TerminateType="ON_LAST_DISCONNECT")
        exit()

def results(testdata, directoryname):    
    path = os.getcwd()+"/"+directoryname
    os.chdir(path)
	
    print('Saving Results')
    stc.perform("SaveResult", CollectResult=True,
                              SaveDetailedResults=True,
                              DatabaseConnectionString="results.db",
                              OverwriteIfExist=True)
   
    stc.perform("CsSynchronizeFiles")
    print('Terminating Session')
    resdir = os.getcwd()
    print("Result Directory: ", resdir)
    stc.perform("ChassisDisconnectAll")
    stc.perform("CSTestSessionDisconnect",Terminate="TRUE")

try:                                                                        
	for i,file in enumerate(testdata["tcc_configurationfile"]):
	    originaldir = os.getcwd()
	    labserver = testdata["labserver"]
	    testcasenumber = "TestCase "+str(i+1)
	    print("------------------------ Starting", testcasenumber, "------------------------")
	    stc.new_session(server=labserver, session_name="cisco", user_name="Spirent",existing_session="join")	 
	    stc.config("AutomationOptions", logTo="stcapi.log", logLevel="INFO")
	    	       
	    now = datetime.now()
	    current_time = now.strftime("%Y-%m-%d %H-%M-%S") 
	    ersp = stc.get("system1", "children-spirent.results.EnhancedResultsSelectorProfile")
	    if ersp == "":
	        ersp = stc.create("spirent.results.EnhancedResultsSelectorProfile", under="system1", SubscribeType="ALL", ConfigSubscribeType="ALL",EnableLiveDataRetention=True)  
	    tcc_configurationfile = file
	    stc.perform("ResetConfigCommand")
	    print("Loading TCC configuration Now -> ", tcc_configurationfile)
	    stc.perform("LoadFromDatabaseCommand", DatabaseConnectionString=tcc_configurationfile)
	    project = stc.get("system1", "children-project")
	    test_info = stc.get(project, 'children-testinfo')
	    TestName = testdata["TestName"][int(i)]
	    print("TestName:",TestName)
	    stc.config(test_info, TestName=TestName)
	    directoryname = current_time+"-"+TestName
	    os.mkdir(directoryname)  
	    
	    if testdata["ipv4"] == "True":  
	        ipv4deviceconfig(testdata) 
	        
	    if testdata["ipv6"] == "True":
	        ipv6deviceconfig(testdata)   
	    
	    runtest(testdata)
	    TemplateName = testdata["TemplateName"][int(i)]
	    print("TemplateName:",TemplateName)
	    filename = testdata["ReportName"][int(i)]
	    print("ReportFilename: ",filename)
	    stc.perform("spirent.results.CreateEnhancedResultsReport", ReportTemplateName=TemplateName, FileName=filename)
	    results(testdata,directoryname) 
	    print("Done", testcasenumber,"\n")
	    if len(testdata["tcc_configurationfile"])>1:
	        time.sleep(15)
	        os.chdir(originaldir)

	    
except Exception as e:
    print("\n", 'ERROR ON LINE {}'.format(sys.exc_info()[-1].tb_lineno), type(e).__name__, e)
    results(testdata,directoryname)

  
  
  