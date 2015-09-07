# -*- coding: utf8 -*-
#
# Copyright (C) 2014 NDP Systèmes (<http://www.ndp-systemes.fr>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

{
    'name': 'Stock Planning Improved',
    'version': '0.1',
    'author': 'NDP Systèmes',
    'maintainer': 'NDP Systèmes',
    'category': 'Warehouse',
    'depends': ['stock_working_days'],
    'description': """
Stock Planning Improved
=======================
This modules implement the improved planning to the stock module.

Improved planning concept
-------------------------
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

Improved planning applied to stock
----------------------------------
In the stock module, the application of the improved planning concepts is the following:

- Tasks are stock moves to be executed.
- Tasks links are links between stock moves made by the procurement rules (make-to-order)
- The due date of a move is the date of the procurement order. It is represented by the "date" field of the stock move.
- The planned date of the move is the date at which we suppose the move will be performed. It is represented by the
  "date expected" field of the stock move.
- If a procurement is rescheduled, the "date" fields of its stock moves are also modified to reflect the new date. If
  one of the move has previous moves (make-to-order configuration), the procurement date for the previous moves is also
  modified, which will modify the date of the previous moves in turn.
- If a stock move is done at a given date and has a following move, the "date expected" of the latter will be updated
  accordingly.
- When "date" and "date expected" are updated, the delay taken between moves is the one of the procurement rule which
  generated the move.

Notes
-----
- This module interfaces with the other planning improved modules such as purchase and mrp.
- This module depends on stock_working_days module since no decent planning can be done without taking into account
  the working days.

""",
    'website': 'http://www.ndp-systemes.fr',
    'data': [
        'stock_planning_improved_view.xml',
    ],
    'demo': [
        'stock_planning_improved_demo.xml',
    ],
    'test': [],
    'installable': True,
    'auto_install': False,
    'license': 'AGPL-3',
    'application': False,
}
