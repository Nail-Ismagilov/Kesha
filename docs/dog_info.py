import os
import datetime
import pandas as pd

_sex = ("hundin", "rude")
_age = ("erwachsen", "welpe")
SEX = {"Hündinen" : "hundin", "Rüden" : "rude", 
       "Welpen_Madchen" : "hundin", "Welpen_und_Junghunde" : "rude"}
AGE = {"Hündinen" : "erwachsen", "Rüden" : "erwachsen", 
       "Welpen_Madchen" : "welpe", "Welpen_und_Junghunde" : "welpe"}
       
name =[]
sex =[]
age =[]
date_of_change =[]
status =[]

def __get_dogs(gender):
    return os.listdir(f"../hunde/{gender}")

def __get_gender(dog):
    return SEX.get(dog)

def __get_age(gender):
    return AGE.get(gender)
    
def __get_time_of_change(gender, dog):
    changeTime = os.path.getmtime(f"../hunde/{gender}/{dog}")
    return datetime.datetime.fromtimestamp(changeTime)

def get_dogs(new=False, old=False):
    """ # generates a pandoc data in csv format
        - Name         // "Name"
        - Date of post // dd/mm/yy
        - Sex    // "Rüde", "Hündin"
        - Age    // "Erwachsen" or "Welpe"
        - Status //  "Vorhanden", "Neu", "Zuhause gefunden"
    """
    vermittlung = os.listdir("../hunde")
    for gender in vermittlung:
        dogs = os.listdir(f"../hunde/{gender}")
        for dog in dogs:
            name.append(dog)
            sex.append(__get_gender(gender))
            age.append(__get_age(gender))
            date_of_change.append(__get_time_of_change(gender,dog))
            status.append("vorhanden")

    # Create a sample dataframe
    dogs_data = {'Name': name,
                 'Date of change' : date_of_change,
                 'Sex': sex,
                 'Age': age,
                 'Status' : status
            }
    df = pd.DataFrame(dogs_data)

    # Save the dataframe to a CSV file
    if new:
        df.to_csv('dogs_new_data.csv', index=False, encoding="utf-8")
    elif old:
        df.to_csv('dogs_old_data.csv', index=False, encoding="utf-8")

    return df

def read_dogs_csv(file):
    return pd.read_csv(file)

def get_group_of_dogs(dataFrame, gender, age):
    filteredData = dataFrame[(dataFrame['Sex'] == gender) & (dataFrame['Age'] == age)]
    print(filteredData)
     

def create_report():
    newDogSet = get_dogs()
    oldDogSet = read_dogs_csv('dogs_old_data.csv')
    ####
    ## filter Rüden erwachsen on both lists
    ## filter Hündin erwachsen
    ## filter Rüden welpen
    ## filter Hündin welpen
    #####
    for gender in _sex:
        for age in _age:
            get_group_of_dogs(oldDogSet, gender, age)

    ## get differences
    ## if it is in the old list and not in the new list -> Zuhause gefunden
    ## if it is in the new list and not in the old list -> New Dog
    ## if the dog in both lists                         -> Vorhanden 
    #####
    # newDogSet.to_csv('dogs_new_data.csv', index=False, encoding="utf-8")
    # oldDogSet.to_csv('dogs_old_data.csv', index=False, encoding="utf-8")
    pass

def check_difference(): 
    df1 = read_dogs_csv('dogs_old_data.csv')
    # df2 = get_dogs(new=True)
    df2 = read_dogs_csv('dogs_new_data.csv')
    df = pd.concat([df2, df1])
    df = df.reset_index(drop=True)
    df_gpby = df.groupby(list(df.columns))
    idx = [x[0] for x in df_gpby.groups.values() if len(x) == 1]
    df.to_csv('dogs_difference_data.csv', index=False, encoding="utf-8")
    # print(df.reindex(idx))
    print("\n")
    df = pd.concat([df1, df2])
    df = df.reset_index(drop=True)
    df_gpby = df.groupby(list(df.columns))
    idx = [x[0] for x in df_gpby.groups.values() if len(x) == 1]

    # Get all diferent values
    df3 = pd.merge(df1, df2, how='outer', indicator='Exist')
    df3 = df3.loc[df3['Exist'] != 'both']


    # If you like to filter by a common ID
    df3  = pd.merge(df1, df2, on="Name", how='outer', indicator='Exist')
    df3  = df3.loc[df3['Exist'] != 'both']

    # print(df3)
    df.to_csv('dogs_difference_data2.csv', index=False, encoding="utf-8")
    datasFrame = df3[df3['Exist'] == 'left_only']
    vorhanden = datasFrame['Name']
    for name in vorhanden:
        
    print(vorhanden)
check_difference()
# create_report()
# create_pandoc()
# read_pandoc_csv()
