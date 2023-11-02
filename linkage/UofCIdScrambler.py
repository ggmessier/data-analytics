import hashlib
from tkinter import filedialog
import tkinter as tk

qGrmValues = [ 2, 3 ]
filterLenValues = [ 32, 64 ]

def bloom_filter(plnTxt, saltStr, qGrmLen=2, filterLen=32):
    
    plnTxt = f'_{plnTxt}_'
    bloomFilter = 0
        
    for i in range(len(plnTxt)-qGrmLen+1):
        byteStr = (saltStr + plnTxt[i:i+qGrmLen]).encode('utf-8','replace')
    
        idxMd5 = int( hashlib.md5(byteStr).hexdigest(), 16) % filterLen
        idxSha = int( hashlib.sha256(byteStr).hexdigest(), 16) % filterLen
        
        bloomFilter |= 1 << idxMd5
        bloomFilter |= 1 << idxSha
        
    return bloomFilter

def scramble_selected_columns():
    
    # Query scrambled file name.
#    scrambledFileName = '/Users/gmessier/tmp/00FakeScrambledInfo.csv'
    
    scrambledFileName = filedialog.asksaveasfilename(
        initialdir='/',
        title="Save scrambed data as...",
        filetypes=(("all files","*.*"),("csv",".*csv"))
    )

    scrambledFile = open(scrambledFileName,'w')
    

    # Clear window.
    for widget in rootWin.winfo_children():
        widget.pack_forget()
    tk.Label(rootWin,width=20,height=10,text='Working...').pack()
    rootWin.update()
    
    # Retrieve key.
    key = scramblingKey.get().strip()    
    
    # Extract column list.
    colSelected = []
    indSelected = []
    
    ind = 0
    for check in rootWin.colChecks:
        if check.get()==1:
            colSelected += [ colNames[ind] ]
            indSelected += [ ind ]
        ind += 1
    
    # Check Bloom filter settings.
    if defaultBloom.get():
        
        # Write header.
        scrambledFile.write(','.join(colNames)+'\n')

    # Modify header for full Bloom output.
    else:
        fullSuffx = []
        for q in qGrmValues:
            for f in filterLenValues:
                fullSuffx += [ f'_q{q}f{f}' ]
        
        colNamesBloom = []
        for i in range(len(colNames)):
            if i in indSelected:
                colNamesBloom += [ colNames[i]+s for s in fullSuffx ]
            else:
                colNamesBloom += [ colNames[i] ]
        
        scrambledFile.write(','.join(colNamesBloom)+'\n')
        

    
    # Scramble selected columns.
    identifyingFile = open(identifyingFileName)
    _ = identifyingFile.readline()

    for row in identifyingFile:
        fields = row.strip().split(',')
        
        # Generate default Bloom filter output.
        if defaultBloom.get():
            for i in indSelected and len(fields[i]) > 0:
                fields[i] = f'{bloom_filter(fields[i],saltStr=key):x}'

            scrambledFile.write(','.join(fields)+'\n')
            
        # Generate full Bloom filter output.
        else:
            fieldsBloom = []
            for i in range(len(fields)):
                if i in indSelected:
                    for q in qGrmValues:
                        for f in filterLenValues:
                            if len(fields[i]) > 0:
                                fieldsBloom += [ f'{bloom_filter(fields[i],saltStr=key,qGrmLen=q,filterLen=f):x}' ]
                            else:
                                fieldsBloom += [ fields[i] ]
                else:
                    fieldsBloom += [ fields[i] ]
                    
            scrambledFile.write(','.join(fieldsBloom)+'\n')
                    
                    
    
    scrambledFile.close()
    
    # All done.
    rootWin.destroy()
    
    

rootWin = tk.Tk()
rootWin.title('Identifying Information Scrambler')
rootWin.wait_visibility()


# --- Select identifying information CSV file. ---
identifyingFileName = filedialog.askopenfilename(
    initialdir='/',
    title="Select Identifying Information CSV File",
    filetypes=(("all files","*.*"),("csv",".*csv"),("pkl",".*pkl"))
)
#identifyingFileName = '/Users/gmessier/tmp/00FakeIdentifyingInfo.csv'


# --- Open and read column header names. ---
identifyingFile = open(identifyingFileName,'r')
colNamesRaw = identifyingFile.readline().split(',')
identifyingFile.close()

# Remove special characters.
colNames = [ c.encode('ascii','ignore').decode().strip() for c in colNamesRaw ]

# --- Query key and which columns should be scrambled. ---
winStr = 'Enter scrambling key (8 to 10 letters and numbers):'
tk.Label(rootWin,text=winStr).pack()
scramblingKey = tk.Entry()
scramblingKey.pack()

winStr = 'Select which columns should be scrambled:'
winLabel = tk.Label(rootWin,text=winStr)
winLabel.pack()

rootWin.colChecks = []
for col in colNames:
    var = tk.IntVar()
    tk.Checkbutton(rootWin, text=col, variable=var, width=20, anchor='w').pack()
    rootWin.colChecks += [ var ]
    
b = tk.Button(text='Scramble Selected Columns', command=scramble_selected_columns).pack()
        
winStr = '''
University of Calgary 
Bloom Filter Scrambling Utility
Contact: Dr. Geoffrey Messier (gmessier@ucalgary.ca)
Version: 1.1
'''

tk.Label(rootWin,text=winStr).pack()

defaultBloom = tk.IntVar()
defaultBloom.set(0)
#winStr = 'Use default Bloom filter settings.'
#tk.Checkbutton(rootWin, text=winStr, variable=defaultBloom, width=25, anchor='w').pack()


#readFile = pd.read_csv(root.filename)


rootWin.mainloop()
