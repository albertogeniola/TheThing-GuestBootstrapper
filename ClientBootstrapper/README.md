## TheThing: Client bootstrapper
This module is a simple bootstrapper for GuestAgents. Its goal is to query the network via UDP broadcast messages, 
in order to discover the sniffer. Once found, it sends some information regarding the current version of the underlying 
operating system. The sniffer, in turn, sends back the URL of the GuestAgent binaries to download and provides 
the network location of the HostController.  

To work correctly, the bootstrapper needs to be scheduled at system startup and must run with highest privileges. 
At the time of writing, only Windows 7 SP1 32 bit is supported. A convenient MSI installer bundle has been prepared
to facilitate even more the installation of the bootstrapper on the client machine. 
