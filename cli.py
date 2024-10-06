HUNDINEN        = "1"
RUDEN           = "2"
WELPEN_RUDEN    = "3"
WELPEN_MADCHEN  = "4"
PFLEGESTELLE    = "5"
ALL             = "6"
EXIT            = "E"

dogs_dict = {HUNDINEN: "Hündinen", 
             RUDEN : "Rüden", 
             WELPEN_RUDEN : "Welpen_und_Junghunde", 
             WELPEN_MADCHEN : "Welpen_Madchen", 
             PFLEGESTELLE : "Pflegestelle",
             ALL : "ALL", 
             EXIT : "Exit"}

class CLI:
    def create_menu(self):
        print()
        print("============================" + "       /^-^\\")
        print("1 - Hündinen                " + "      / o o \\")
        print("2 - Rüden                   " + "     /   Y   \\")
        print("3 - Welpen_Madchen          " + "     V \\ v / V")
        print("4 - Welpen_und_Junghunde    " + "       / - \\" )
        print("5 - Pflegestelle            " + "      /    |")
        print("6 - ALL                     " + "(    /     |")
        print("E - Exit                    " + " ===/___) ||")
        print("============================" )

    def show_report(reportData):
        for data in reportData.keys():
            print(f"{data.upper()}:")
            count = 0
            for dog in data:
                count += 1
                print(f"{count} - {dog}")
