# Developer:    Tyler Pereira
# Created:      07192018
# Modified:     07192018
# Description:  GUI to collect and analyze nvme driver trace events logged in linux kernel debug folder.
# Requirements: Linux kernel 4.17 or later is required


from Tkinter import *
import ttk
import os, subprocess, sys, re, webbrowser
import Tkinter, tkFileDialog
 
def donothing():
   x = 0

def openSpec():
    webbrowser.open("https://nvmexpress.org/wp-content/uploads/NVM_Express_Revision_1.3.pdf",new=1)

def collect_trace_log():

    # copy trace buffer to current directory and allow user to read file
    subprocess.check_call(["sudo","cp","/sys/kernel/debug/tracing/trace","./"])
    subprocess.check_call(["sudo","chmod","-R","0777","trace"])

    # Init file IO
    trace_buffer   = open("trace","rb")
    trace_file     = open("trace.log","wb+")
    trace_history  = open("trace_history.log","ab+")

    # Populate trace files
    for line in trace_buffer:
        trace_file.write(line)
        trace_history.write(line)

    trace_buffer.close()
    trace_file.close()
    trace_history.close()

def save_trace():
    root = Tkinter.Tk()
    root.withdraw()

    file_path = tkFileDialog.asksaveasfilename()
    filename = file_path.split("/")[-1]
    root.destroy()
    os.system("cp trace.log "+filename)


def onOpen():

    root = Tkinter.Tk()
    root.withdraw()

    file_path = tkFileDialog.askopenfilename()
    filename = file_path.split("/")[-1]
    root.destroy()
    os.system("cp "+filename+" trace.log")

    # Populate treeview with trace evetns
    populate_treeview()



def toDo():
    # Init popup window
    popup = Tk()
    popup.wm_title("TODO")

    # Init button
    B1 = ttk.Button(popup, text="Exit", command = popup.destroy)
    B1.pack(side="bottom")

    # Set geometry and kickoff popup loop
    popup.geometry("200x200")
    popup.mainloop() 


def capture():
    # Clear trace buffer in case it exists
    os.system("echo| sudo tee /sys/kernel/debug/tracing/trace")

    # Enable nvme event tracing
    os.system("echo 1| sudo tee /sys/kernel/debug/tracing/events/nvme/enable")


def stop_capture():
    # Disable nvme event tracing
    os.system("echo 0| sudo tee /sys/kernel/debug/tracing/events/nvme/enable")

    # Capture everything in trace buffer and save copy in local directory
    collect_trace_log()

    # Populate treeview with trace evetns
    populate_treeview()

def remove_dup(duplicate):
    no_dups = []
    for ID in duplicate:
        if ID not in no_dups:
            no_dups.append(ID)
    return no_dups

def prompt_sudo():
    ret_val = 0
    if os.geteuid() != 0:
        prompt = "[sudo] password for %u:"
        ret_val = subprocess.check_call("sudo -v -p '%s'" % prompt, shell=True)
    return ret_val

def init_menubar():

    # Gross function to init munebar
    file_menu = Menu(menubar, tearoff=0)
    file_menu.add_command(label="Open", command=onOpen)
    file_menu.add_command(label="Save Trace", command=save_trace)
    file_menu.add_separator()
    file_menu.add_command(label="Export to csv", command=toDo) #TODO
    menubar.add_cascade(label="File", menu=file_menu)
     
    trace_menu = Menu(menubar, tearoff=0)
    trace_menu.add_command(label="Capture", command=capture)
    trace_menu.add_command(label="Stop Capture", command=stop_capture)
    menubar.add_cascade(label="Trace Options", menu=trace_menu)

    report_menu = Menu(menubar, tearoff=0)
    report_menu.add_command(label="Performance", command=toDo) #TODO
    menubar.add_cascade(label="Reports", menu=report_menu)

    help_menu = Menu(menubar, tearoff=0)
    help_menu.add_command(label="NVMe Spec", command=openSpec)
    help_menu.add_command(label="README", command=toDo) #TODO
    menubar.add_cascade(label="Help", menu=help_menu)


def init_treeview():

    # Gross function to init munebar
    tree['show'] = 'headings'
    tree["columns"]=("CMD","NSID","CMDID","QID","FUSE","PSDT","MPTR","CMD_Specific_Info","Latency")
    
    tree.column("CMD", width=100, anchor="c")
    tree.column("NSID", width=25, anchor="c")
    tree.column("CMDID", width=25, anchor="c")
    tree.column("QID", width=25, anchor="c")
    tree.column("FUSE", width=25, anchor="c")
    tree.column("PSDT", width=25, anchor="c")
    tree.column("MPTR", width=25, anchor="c")
    tree.column("CMD_Specific_Info", width=250, anchor="c")
    tree.column("Latency", width=50, anchor="c")

    tree.heading("CMD", text="CMD")
    tree.heading("NSID", text="NSID")
    tree.heading("CMDID", text="CMDID")
    tree.heading("QID", text="QID")
    tree.heading("FUSE", text="FUSE")
    tree.heading("PSDT", text="PSDT")
    tree.heading("MPTR", text="MPTR")
    tree.heading("CMD_Specific_Info", text="CMD Specific Info")
    tree.heading("Latency", text="Latency (us)")


def populate_treeview():
    
    # Clear previous trace
    tree.delete(*tree.get_children())

    # Init trace dict and array to hold array cmd ID and dict for all cmds with that unique cmd ID
    trace_dict = {}
    trace_array = []
    
    # Iterate through trace file and append cmd ID to array and cmds w/ cmd ID to dict
    trace_file     = open("trace.log","rb+")
    for line in trace_file:
        if "nvme_" in line:
            cmdID = line.split("cmdid=")[1].split(",")[0]
            trace_array.append(cmdID)
            if cmdID in trace_dict:
                trace_dict[cmdID] += "; " + line
            else:
                trace_dict[cmdID] = line
    trace_file.close()

    # Remove any duplicate instances of cmd ID in array
    trace_array = remove_dup(trace_array)


    for index,cmdID in enumerate(trace_array):

        # Parse all global common fields between NVMe and Admin CMDs

        # Parse first and last event in cmd ID
        first_trace_event_in_cmd    = trace_dict[cmdID].split(";")[0]
        last_trace_event_in_cmd     =  trace_dict[cmdID].split(";")[-1]

        # Calculate response time -> Timestamp is in us
        timestamp       = re.findall("\d+\.\d+", first_trace_event_in_cmd.split(": nvme_")[0])[0]
        last_timestamp  = re.findall("\d+\.\d+",last_trace_event_in_cmd.split(": nvme_")[0])[0]
        response_time   = round(float(last_timestamp) - float(timestamp), 4)

        # Parse cmd name/opcode
        cmd             = first_trace_event_in_cmd.split("cmd=(")[1].split(" ")[0]

        # Parse flags field for FUSE and PSDT
        flags           = first_trace_event_in_cmd.split("flags=")[1].split(",")[0]
        scale           = 16 ## equals to hexadecimal
        num_of_bits     = 8
        bin_flags       = bin(int(flags, scale))[2:].zfill(num_of_bits)
        fuse            = hex(int(bin_flags[:2],2)) 
        psdt            = hex(int(bin_flags[:-2],2))
        
        # Parse MPTR
        mptr            = first_trace_event_in_cmd.split("meta=")[1].split(",")[0]

        # Parse other cmd specific data
        cmdSpecific     = first_trace_event_in_cmd.split("cmd=")[1].replace("(","").replace(")","").split(' ', 1)[1]

        # Different tree insert for Admin cmds
        if "nvme_admin" in first_trace_event_in_cmd:
            tree.insert("" , index,    text="Line "+str(index), values=(cmd,"-",cmdID,"-",fuse,psdt,mptr,cmdSpecific,str(response_time)))

        # Insert IO cmds to tree w/ other fields
        elif "nvme_cmd" in first_trace_event_in_cmd:
            # Parse QID and NSID specific to IO cmds
            qid     = first_trace_event_in_cmd.split("qid=")[1].split(",")[0]
            nsid    = first_trace_event_in_cmd.split("nsid=")[1].split(",")[0]

            tree.insert("" , index,    text="Line "+str(index), values=(cmd,nsid,cmdID,qid,fuse,psdt,mptr,cmdSpecific,str(response_time)))

        else:
            tree.insert("" , index,    text="Line "+str(index), values=(cmd,"-",cmdID,"-","-","-","-","-",str(response_time)))
        
        # Bind double click to the treeview item
        tree.bind("<Double-1>", lambda event: OnDoubleClick(event, cmd_dict = trace_dict))
        
        #csv_file = open("CSV_FILE.txt", 'wb')
        #writer = csv.writer(csv_file)
        #for child in tree.get_children():
        #    print(tree.item(child)["values"])
        #    writer.writerows(tree.item(child)["values"])

        
def OnDoubleClick(event, cmd_dict):

    # Capture item selected
    item = tree.identify('item',event.x,event.y)

    # Parse cmd ID from item
    cmdID = tree.item(item)['values'][2]

    # Generate popup with all cmds that have unique cmd ID
    popup_message(cmd_dict[str(cmdID)], cmdID)      

def popup_message(msg, cmdID):
    
    # Init popup window
    popup = Tk()
    popup.wm_title("All Events for CMDID = " + str(cmdID))

    # Init listbox
    listbox = Listbox(popup)
    listbox.pack(side="top", fill="both", pady=10,expand=True)

    # Init button
    B1 = ttk.Button(popup, text="Exit", command = popup.destroy)
    B1.pack(side="bottom")

    # Add trace events to list box
    items=msg.split(";")
    for index,item in enumerate(items):
        listbox.insert(index,item.strip())

    # Set geometry and kickoff popup loop
    popup.geometry("1200x400")
    popup.mainloop() 


# Global Widgets I want to access
root = Tk()
menubar = Menu(root)
tree = ttk.Treeview(root)


def main():
    # Check for Sudo Priviliges 
    if prompt_sudo() != 0:
        print "Exiting... Need sudo privileges to function."
        sys.exit()
   
    else:
        # Run GUI
        root.title("NVMe Sniffer")
        root.geometry("1200x800")
        
        # Initti menubar
        init_menubar()
        root.config(menu=menubar)

        # Init treeview
        init_treeview()
        tree.pack(side="left", fill="both", expand=True)
        
        # Kickoff root loop
        root.mainloop()

if __name__ == "__main__":
    main()

