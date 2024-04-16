HUNDINEN        = "1"
RUDEN           = "2"
WELPEN_RUDEN    = "3"
WELPEN_MADCHEN  = "4"
ALL             = "5"
EXIT            = "E"

dogs_dict = {HUNDINEN: "Hündinen", 
             RUDEN : "Rüden", 
             WELPEN_RUDEN : "Welpen_und_Junghunde", 
             WELPEN_MADCHEN : "Welpen_Madchen", 
             ALL : "ALL", 
             EXIT : "Exit"}

class CLI:
    def create_dog():
        print()
        print("       /^-^\\")
        print("      / o o \\")
        print("     /   Y   \\")
        print("     V \\ v / V")
        print("       / - \\" )
        print("      /    |")
        print("(    /     |")
        print(" ===/___) ||")
        print("vvvvvvvvvvvvvvvvvvvvvvvvvvvv")

    def create_menu():
        print("============================")
        print(f"1 - {dogs_dict[HUNDINEN]}\n"
            f"2 - {dogs_dict[RUDEN]}\n"
            f"3 - {dogs_dict[WELPEN_RUDEN]}\n"
            f"4 - {dogs_dict[WELPEN_MADCHEN]}\n"
            f"5 - {dogs_dict[ALL]}\n"
            f"{EXIT} - {dogs_dict[EXIT]}")
        print("============================")

    def show_report(reportData):
        for data in reportData.keys():
            print(f"{data.upper()}:")
            count = 0
            for dog in data:
                count += 1
                print(f"{count} - {dog}")
