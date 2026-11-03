# WFP Candidate Dashboard

I want to lay the groundwork for setting up a Working Families Party candidate dashboard.  We're going to use the data stored in `candidates.json` to power this dashboard.  

The dashboard UI will be composed of two major sections: 
1. a tile grid map representing the 50 states + DC with toggles for different levels of office; this map will effectively be a tool for applying filters to the other section, the candidate list view
2. a candidate list displaying info about the candidates based on the filter settings set in the map view

Visually, on a desktop view, the tile map will take up the left half of the view, and the candidate list will be on the right-hand side of the view.  On a mobile view I want the map element to be stacked on top of the candidate list.


## US State Tile Grid Map  

The map view will be the most complex part of this dashboard.  I want to develop it in a modular way that will make it easy to maintain and expand on in the future.  As such, I want to develop this part of the UI as a set of reusable frontend components. The map view will be composed of equal sized square tiles arranged in such away that roughly emulates the map of the United States.  


### Tile component 

The square tiles will be the base component that is re-used to build the map.  Visually the tiles components should have a label prominently displayed in the middle of the tile; this label will typically be the two letter state abbreviation. The tiles should have visibly clear borders that are distinct from the tiles background color.  Typically the border and label color should be a bolder, darker color and the background should be a much lighter shade of that primary color.  

Tiles will also have "notches" in each corner.  These notches wont always be visible, but will be togglable based on various other attributes.  Each title can have a total of four notches, one for each corner, i.e. the upper left corner, the upper right corner, the lower left corner, and the lower right corner.  Visually, the notches should be the same darker, bolder primary color used for the title's border and label.  Visually, a notch will effectively be a little right triangle aligned neatly with one of the corners of a tile.  A notch's sides should be around a quarter to a third the length of a square tile's side and align with the respective corners a tile; just big enough to be visibly prominent at a glance, but not so big to obscure the tile's label.  

Each tile will have attributes that reflect various aspects of WFP's candidate endorsements for a given state.  Specifically, we're going to be starting off with at least this set of attributes for each square state tile:

- `state_name` - the name of the state
- `state_abbreviation` - i.e. the standard two letter abbreviation for the state; we'll use this as the label for the title; it should be displayed prominently in the center of the title
- `has_wfp_endorsments` - boolean value; will be represented visually; if false, the state tile should be a muted gray color; if true, the state tile should be highlighted somehow; if `has_wfp_endorsments` it implies that at least one of the attributes: `has_federal_senate`, `has_state_house`, `has_state_senate`, `has_state_executive`, `has_judicial`, `has_local_office`, or `has_ballot_measure` is set to true
- `has_federal_house` - boolean value; this will toggle the visibility of the upper left notch
- `has_federal_senate` - boolean value; toggles the upper right notch
- `has_state_house` - boolean value; toggles the lower left notch
- `has_state_senate` - boolean value; toggles the lower right notch
- `has_state_executive` - boolean value; (not surfacing visually at first)
- `has_judicial` - boolean value; (not surfacing visually at first)
- `has_local_office` - boolean value; (not surfacing visually at first)
- `has_ballot_measure` - boolean value; (not surfacing visually at first)


### Map component 

The map component is composed of tile components arranged in a grid-like layout.  It represents the 50 U.S. states + DC in a checker board like grid. Each state will be represented by an individual tile component with it's two letter state abbreviation displayed in the middle of the each square as a label. This checker board like layout will require an 11 by 8 grid: 11 squares wide, running "west" to "east"; and 8 squares tall, running "north" to "south".  In the table below, I've listed the coordinates where each state square will be located on the grid.  The grid starts in the most northwestern part of the map at square 1,1 and the most southeastern square is at 11,8.

| State Name                  | State Abbreviation | Grid Coordinates |
| ----------------------------|--------------------|------------------|
| Alabama                     | AL                 | 7,7              |
| Alaska                      | AK                 | 1,1              |
| Arizona                     | AZ                 | 2,6              |
| Arkansas                    | AR                 | 5,6              |
| California                  | CA                 | 1,5              |
| Colorado                    | CO                 | 3,5              |
| Connecticut                 | CT                 | 10,4             |
| Delaware                    | DE                 | 10,5             |
| District of Columbia        | DC                 | 9,6              |
| Florida                     | FL                 | 9,8              |
| Georgia                     | GA                 | 8,7              |
| Hawaii                      | HI                 | 1,8              |
| Idaho                       | ID                 | 2,3              |
| Illinois                    | IL                 | 6,3              |
| Indiana                     | IN                 | 6,4              |
| Iowa                        | IA                 | 5,4              |
| Kansas                      | KS                 | 4,6              |
| Kentucky                    | KY                 | 6,5              |
| Louisiana                   | LA                 | 5,7              |
| Maine                       | ME                 | 11,1             |
| Maryland                    | MD                 | 9,5              |
| Massachusetts               | MA                 | 10,3             |
| Michigan                    | MI                 | 7,3              |
| Minnesota                   | MN                 | 5,3              |
| Mississippi                 | MS                 | 6,7              |
| Missouri                    | MO                 | 5,5              |
| Montana                     | MT                 | 3,3              |
| Nebraska                    | NE                 | 4,5              |
| Nevada                      | NV                 | 2,4              |
| New Hampshire               | NH                 | 11,2             |
| New Jersey                  | NJ                 | 9,4              |
| New Mexico                  | NM                 | 3,6              |
| New York                    | NY                 | 9,3              |
| North Carolina              | NC                 | 7,6              |
| North Dakota                | ND                 | 4,3              |
| Ohio                        | OH                 | 7,4              |
| Oklahoma                    | OK                 | 4,7              |
| Oregon                      | OR                 | 1,4              |
| Pennsylvania                | PA                 | 8,4              |
| Rhode Island                | RI                 | 11,4             |
| South Carolina              | SC                 | 8,6              |
| South Dakota                | SD                 | 4,4              |
| Tennessee                   | TN                 | 6,6              |
| Texas                       | TX                 | 4,8              |
| Utah                        | UT                 | 2,5              |
| Vermont                     | VT                 | 10,2             |
| Virginia                    | VA                 | 8,5              |
| Washington                  | WA                 | 1,3              |
| West Virginia               | WV                 | 7,5              |
| Wisconsin                   | WI                 | 6,2              |
| Wyoming                     | WY                 | 3,4              |




## Candidate list UI controls

This US State Tile Grid Map Component will be the primary UI element of map half of the dashboard. When the user clicks on a state, the candidate list should only display races for that state.  When a state is an active filter, it should be visually distinct somehow.

Below the map I also want to include toggle elements (effectively check boxes) to toggle the candidate list view based on the `office_category`.  


## Candidate list view

The candidate list view will display a list of the candidates endorsed by WFP. By default it will list everything.  This section should scroll independently from the map section.  It should update and respond in real-time to any of the elements toggled in 


## Style Guide

We're going to loosely follow the WFP's Style Guide.  

### Colors

Primary Color, WFP Orange: #f4563c
Secondary Color, WFP Marigold: #fecc08
Tertiary Color, WFP Purple: #461f82
WFP Yellow: #eaf96e
WFP Gray: #e9e7df

### Fonts

These are the official fonts specified by WFP style guide.  PF Venue Condensed is a proprietary typeface, so for now use your best judgment for a reasonable substitute.  If in doubt, just use Helvetica.

Headline font: PF Venue Condensed Bold
Sub-headline font: PF Venue Condensed Light
Body copy: Helvetica Neue Regular


## Coding Preferences and Final output

I want the initial version of this to be packaged as a static .html file with all the necessary javascript logic baked directly in.  Initially, I want to host this on a github page.  We shouldn't need any back end logic for this.  

I prefer to work with Vuejs and Tailwindcss.  I'm not sure if it's overkill to enforce typescript too.  

