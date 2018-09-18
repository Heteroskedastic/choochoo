
A training diary written mainly for myself, but perhaps attractive to others
who also want a way to track and plan their progress that is open, lightweight
and extensible.

The main interface is a curses-style diary, used to track daily activity
as well as progress towards aims.  A flexible "schedule spec" is used to
define periodic events (eg training routines) and (unfortunately) there's 
dedicated functionality for tracking injuries.

Data can be imported from FIT files (from smart watches and bike computers)
and summary statistics generated monthly or annually.  All data are stored
in an sqlite3 relation database.  For plotting and analysis they can be 
exported to pandas data frames in a Jupyter notebook.

Above all, the system is *open and extensible*.  You can define your own 
training plans.  You can hack the code.  The code is structured so that you
can re-use the parts you need (ORM for database?  library to read FIT files?
it's all available).  

One omission that may be important to some people is the (purposeful)
lack of emphasis on power meters.

* [Activities](activities) - import and organise activity data.
* [Analysis](analysis) - explore data in Jupyter notebooks. 
* [FIT Files](fit-files) - display FIT format data.