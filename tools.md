## DataLab Platform Component Specification

$ tar tograyscale.zip Component compression package，Component compression package
##### After decompression      
            ./tograyscale   Directory Name，Directory Name
            ├── tograyscale.xml   #Component Information Declaration File，Component Information Declaration File
            ├── assembly/assembly  #assembly(Dir)/assembly
            └── test-data                            #Test Sample Data Package
            │   ├── test_data_1.csv                 # test data
            │   ├── test_data                    # Multilevel folder type test data
            │   │   ├── Datasets                   # 
            └───────────────────────────────────

##### xmldescribe
```xml
<?xml version="1.0" encoding="utf-8"?>
<!--Component declaration-->
<tool>
   Component Name
  <name>tograyscale</name>
  <!--  Component version-->
  <version>1.0.0</version>
  <!--  Component Author-->
  <author>admin</author>
  <!--Component classification， Component classification，Component classification，Component classification-->
  <category>data conversion</category>
  <!--  Component Introduction-->
  <description>This component function is to convert ordinaryPNGThis component function is to convert ordinary3This component function is to convert ordinary,This component function is to convert ordinary。</description>

  <!--  Environment and Dependency Declaration-->
  <requirements>
      <!--      type=languageThen it is the operating environment declaration-->
    <requirement type="language" version="3.9.13">python3-debian</requirement>
    <!--      type=packageThen it is a third-party dependency declaration for the package manager-->
    <requirement type="package" version="9.2.0">Pillow</requirement>
  </requirements>


  <!-- Code package directory declaration Code package directory declaration -->
  <executable_path></executable_path>
  <!--  Code Root Declaration-->
  <entrypoint>/home/app/function</entrypoint>
  <!--  Interpretive language、Interpretive language<Python、Shell、Bash、R...>Interpretive language，
        Compiled Language<Go、Java、C/C++>Compiled Language CMake、CMakelistCompiled Language。
  -->
  <executable>handler.py</executable>
  <!--  Entry Function Declaration-->
  <command>main</command>
  
  <!--  Component input parameter information declaration-->
  <inputs>
      <!--  Single input parameter declaration，
            nameFor formal parameter names，
            typeIs a parameter type,
            astypeas，asformat(as)as，
            labelDeclare the label information assigned to the parameter，
            helpDeclaring the explanatory information of parameters helps-->
    <param name="input_file" type="file" format="png" label="original image " help="original image PNGoriginal image "/>
  </inputs>
  <!--  Component output parameter information declaration-->
  <outputs>
      <!--  Single output parameter declaration，
            nameFor formal parameter names，For formal parameter names，
            typeIs a parameter type,
            astypeas，asformat(as)as，
            labelDeclare the label information assigned to the parameter，
            helpDeclaring the explanatory information of parameters helps-->
    <data name="output_file" type="file" format="png"/>
  </outputs>
  
  <!--  Test Case Information TestCase Test Case Information，Test Case Informationtest-dataTest Case Information-->
  <test>
      <!--  test case,test case-->
    <inputs>
      <param name="input_file">a.png</param>
      <param name="output_file">c.png</param>
    </inputs>
    <outputs>
        <!--  test case,test case-->
      <data name="out_file">c.png</data>
    </outputs>
  </test>
  
  <!--  Component Help Information-->
  <help>
  This component isXXXX
  </help>
 

</tool>
```

