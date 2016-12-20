[![Build Status](http://runbot.ndp-systemes.fr/runbot/badge/flat/9/8.0.svg)](http://runbot.ndp-systemes.fr/runbot/repo/ssh-git-gitlab-ndp-systemes-fr-10022-odoo-addons-common-modules-git-9)

# odoo-addons
Public Odoo addons from NDP Systèmes


## Main Features
### Just-In-Time Procurement

Just-In-Time (JIT) is an inventory strategy companies employ to increase efficiency and decrease waste by receiving
goods only as they are needed in the production process, thereby reducing inventory costs.

These modules implement a new calculation method for minimum stock rules that creates procurements for products just
before they are needed instead of creating them at earliest.

Note that this has nothing to do with the badly-named standard "procurement_jit" module.

This feature is implemented in the following modules:

- stock_procurement_just_in_time: Holds the logic of the new calculation of minimum stock rules.
- purchase_procurement_just_in_time: Adds helper messages for the purchasing officers to make the right
  decisions (in particular rescheduling already placed orders with the suppliers) when implementing a 
  just-in-time strategy. 

### Working Days Scheduling

The standard Odoo scheduling of procurements is based on calendar days. These modules enable to schedule 
all the procurement activities (stock, purchase, mrp) on working days instead with the ability to have
different calendars for each warehouse and each supplier.

This feature is implemented in the following modules:

- stock_working_days
- purchase_working_days
- mrp_working_days

### Asynchronous Scheduler

The scheduler in Odoo cannot be monitored and the user has no feedback on what is happening. In 
particular, the scheduler fails silently when an exception is raised and the user has no means 
to know what was the problem.

The Asynchronous Scheduler launches the Odoo Scheduler as a job in the OCA/connector interface.
The jobs can be monitored with the jobs menu and if a job fails the exception raised is shown to 
the user.

This feature is split into the following modules:

- scheduler_async
- scheduler_async_stock

### Planning Improved

The improved planning is a standardization of planning management in Odoo based on the following concepts:

- A planning is made of several tasks linked together. Each task can happen only when all the previous tasks are done.
- Each task has two dates:
    - A due date which is the date before which the task is to be done at the latest. The due date is changed only when
      a major rescheduling occurs. It is calculated backwards, task by task, from the due date of rightmost task of the
      planning (which is usually the date at which we promised to deliver the product to the customer).
    - A planned date which is the date at which we imagine the task is going to be executed given the information we
      have now. The planned date should be changed each time we have a new information and should never be in the past
      (since we are today and the task is not done, we have the information that the task will be executed sometime from
      now, but not before). It is calculated forwards, task by task, from the task(s) currently in execution.
- When a task is done, the actual execution date and the planned date are the same, but the due date is unchanged.
- The only relevant way to measure whether the project is late or early is for each task to compare the due date and
  the planned date.
- Comparing the planned date with today's date gives a indication on the accuracy of the planning, not on whether we
  are late or early.

This improved planning is implemented in the following modules:

- stock_planning_improved: the "date" field of move is used as due date and "date_expected" field as planned date.
- purchase_planning_improved: a new "required_date" field is created to hold the due date and "date_planned" is used as
  the planned date.
  
### Automatic Moves

When dealing with complex logistic routes it is sometimes necessary to have moves automatically processed
without the need of an action from the operator. This is particularly the case when the logistic schema 
separates different products on different routes.

- stock_auto_move module adds the possibility to have move automatically processed as soon as the products are available
in the move source location.

### Grouping Purchase Orders Lines in Draft Purchase Orders (RFQ)

In the standard Odoo implementation purchase order lines generated are grouped in one single RFQ for each supplier. 
This module will instead generate a RFQ for the same supplier grouping only the purchase order lines in a given time 
frame set for this supplier (e.g. one for each week or each month, etc.).

- purchase_group_by_period is best used with the procurement just-in-time modules Miscellaneous

### Putaway Strategies

Putaway strategies are used when a product needs to be putaway in the stock so as to suggest a specific location (bin) 
to the user.

- product_putaway_last will suggest the last location where the product was putaway the last time.
- product_putaway_dispatch will dispatch the products of a stock operations to the different sub-locations 
  according to the outgoing moves in all the sub-locations.

### Miscellaneous

- group_operators adds new operators to the database for aggregation of data when using a "Group By" filter. Currently 
  adds the "first" and "last" operators which give the value of the first or the last grouped line.
- mrp_bom_use_cases adds a tree view on products to see all the BoM which recursively use this product as a component.
- package_weight adds "weight" and "weight net" fields to packs which are automatically calculated from the pack's 
  content and its logistic unit weights.
- stock_product_warning adds a warning flag on a product that can be seen in the transfer screen of stock pickings, as
  well as on barcode interface
- stock_split_picking enables to create a backorder on a stock picking without transfering the initial one for the 
  moment.
