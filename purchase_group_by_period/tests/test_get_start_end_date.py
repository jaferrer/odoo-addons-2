# -*- coding: utf-8 -*-
from openerp.tests import common
from datetime import datetime


class TestPurchaseGroupByPeriod(common.TransactionCase):
    MONTHS = 'months'
    YEARS = 'years'
    DAYS = 'days'
    WEEKS = 'weeks'

    def test_3_month(self):
        print "----------------3 Month---------------"
        date = datetime(2015, 8, 12)
        tf = self._get_tf(3, self.MONTHS)
        date_start, date_end = tf.get_start_end_dates(date)
        print "Date start [%s]" % date_start
        print "Date end [%s]" % date_end
        self.assertEqual(date_start.year, 2015)
        self.assertEqual(date_start.month, 07)
        self.assertEqual(date_start.day, 01)
        self.assertEqual(date_start.hour, 0)
        self.assertEqual(date_start.minute, 0)
        self.assertEqual(date_start.second, 1)

        self.assertEqual(date_end.year, 2015)
        self.assertEqual(date_end.month, 9)
        self.assertEqual(date_end.day, 30)
        self.assertEqual(date_end.hour, 23)
        self.assertEqual(date_end.minute, 59)
        self.assertEqual(date_end.second, 59)

    def test_2_month(self):
        print "----------------2 Month---------------"
        date = datetime(2016, 6, 30)
        tf = self._get_tf(2, self.MONTHS)
        date_start, date_end = tf.get_start_end_dates(date)
        print "Date start [%s]" % date_start
        print "Date end [%s]" % date_end
        self.assertEqual(date_start.year, 2016)
        self.assertEqual(date_start.month, 5)
        self.assertEqual(date_start.day, 01)
        self.assertEqual(date_start.hour, 0)
        self.assertEqual(date_start.minute, 0)
        self.assertEqual(date_start.second, 1)

        self.assertEqual(date_end.year, 2016)
        self.assertEqual(date_end.month, 6)
        self.assertEqual(date_end.day, 30)
        self.assertEqual(date_end.hour, 23)
        self.assertEqual(date_end.minute, 59)
        self.assertEqual(date_end.second, 59)

    def test_1_year(self):
        print "----------------1 Year---------------"
        date = datetime(2016, 7, 3)
        tf = self._get_tf(1, self.YEARS)
        date_start, date_end = tf.get_start_end_dates(date)
        print "Date start [%s]" % date_start
        print "Date end [%s]" % date_end
        self.assertEqual(date_start.year, 2016)
        self.assertEqual(date_start.month, 01)
        self.assertEqual(date_start.day, 01)
        self.assertEqual(date_start.hour, 0)
        self.assertEqual(date_start.minute, 0)
        self.assertEqual(date_start.second, 01)

        self.assertEqual(date_end.year, 2016)
        self.assertEqual(date_end.month, 12)
        self.assertEqual(date_end.day, 31)
        self.assertEqual(date_end.hour, 23)
        self.assertEqual(date_end.minute, 59)
        self.assertEqual(date_end.second, 59)

    def test_2_year(self):
        print "----------------2 Years---------------"
        date = datetime(2016, 7, 3)
        tf = self._get_tf(2, self.YEARS)
        date_start, date_end = tf.get_start_end_dates(date)
        print "Date start [%s]" % date_start
        print "Date end [%s]" % date_end
        self.assertEqual(date_start.year, 2015)
        self.assertEqual(date_start.month, 01)
        self.assertEqual(date_start.day, 01)
        self.assertEqual(date_start.hour, 0)
        self.assertEqual(date_start.minute, 0)
        self.assertEqual(date_start.second, 01)

        self.assertEqual(date_end.year, 2016)
        self.assertEqual(date_end.month, 12)
        self.assertEqual(date_end.day, 31)
        self.assertEqual(date_end.hour, 23)
        self.assertEqual(date_end.minute, 59)
        self.assertEqual(date_end.second, 59)

    def test_10_days(self):
        print "----------------10 days---------------"
        date = datetime(2016, 8, 12)
        tf = self._get_tf(10, self.DAYS)
        date_start, date_end = tf.get_start_end_dates(date)
        print "Date start [%s]" % date_start
        print "Date end [%s]" % date_end
        self.assertEqual(date_start.year, 2016)
        self.assertEqual(date_start.month, 8)
        self.assertEqual(date_start.day, 8)
        self.assertEqual(date_start.hour, 0)
        self.assertEqual(date_start.minute, 0)
        self.assertEqual(date_start.second, 0)

        self.assertEqual(date_end.year, 2016)
        self.assertEqual(date_end.month, 8)
        self.assertEqual(date_end.day, 17)
        self.assertEqual(date_end.hour, 23)
        self.assertEqual(date_end.minute, 59)
        self.assertEqual(date_end.second, 59)

    def test_20_days(self):
        print "----------------20 days---------------"
        date = datetime(2016, 7, 3)
        tf = self._get_tf(20, self.DAYS)
        date_start, date_end = tf.get_start_end_dates(date)
        print "Date start [%s]" % date_start
        print "Date end [%s]" % date_end
        self.assertEqual(date_start.year, 2016)
        self.assertEqual(date_start.month, 06)
        self.assertEqual(date_start.day, 29)
        self.assertEqual(date_start.hour, 0)
        self.assertEqual(date_start.minute, 0)
        self.assertEqual(date_start.second, 0)

        self.assertEqual(date_end.year, 2016)
        self.assertEqual(date_end.month, 07)
        self.assertEqual(date_end.day, 18)
        self.assertEqual(date_end.hour, 23)
        self.assertEqual(date_end.minute, 59)
        self.assertEqual(date_end.second, 59)

    def test_2_week(self):
        print "----------------2 weeks---------------"
        date = datetime(2016, 7, 3)
        tf = self._get_tf(2, self.WEEKS)
        date_start, date_end = tf.get_start_end_dates(date)
        print "Date start [%s]" % date_start
        print "Date end [%s]" % date_end
        self.assertEqual(date_start.year, 2016)
        self.assertEqual(date_start.month, 06)
        self.assertEqual(date_start.day, 20)
        self.assertEqual(date_start.hour, 0)
        self.assertEqual(date_start.minute, 0)
        self.assertEqual(date_start.second, 0)

        self.assertEqual(date_end.year, 2016)
        self.assertEqual(date_end.month, 07)
        self.assertEqual(date_end.day, 03)
        self.assertEqual(date_end.hour, 23)
        self.assertEqual(date_end.minute, 59)
        self.assertEqual(date_end.second, 59)

    def test_2_month_custom1(self):
        print "----------------2 Month custom-1 ---------------"
        date = datetime(2016, 8, 12)
        date_reference = datetime(2016, 7, 15)
        tf = self._get_tf(2, self.MONTHS)
        date_start, date_end = tf.get_start_end_dates(date, date_reference)
        print "Date start [%s]" % date_start
        print "Date end [%s]" % date_end
        self.assertEqual(date_start.year, 2016)
        self.assertEqual(date_start.month, 07)
        self.assertEqual(date_start.day, 15)
        self.assertEqual(date_start.hour, 0)
        self.assertEqual(date_start.minute, 0)
        self.assertEqual(date_start.second, 1)

        self.assertEqual(date_end.year, 2016)
        self.assertEqual(date_end.month, 9)
        self.assertEqual(date_end.day, 14)
        self.assertEqual(date_end.hour, 23)
        self.assertEqual(date_end.minute, 59)
        self.assertEqual(date_end.second, 59)

    def test_2_month_custom2(self):
        print "----------------2 Month custom-2 ---------------"
        date = datetime(2016, 7, 7)
        date_reference = datetime(2016, 7, 15)
        tf = self._get_tf(2, self.MONTHS)
        date_start, date_end = tf.get_start_end_dates(date, date_reference)
        print "Date start [%s]" % date_start
        print "Date end [%s]" % date_end
        self.assertEqual(date_start.year, 2016)
        self.assertEqual(date_start.month, 05)
        self.assertEqual(date_start.day, 15)
        self.assertEqual(date_start.hour, 0)
        self.assertEqual(date_start.minute, 0)
        self.assertEqual(date_start.second, 1)

        self.assertEqual(date_end.year, 2016)
        self.assertEqual(date_end.month, 7)
        self.assertEqual(date_end.day, 14)
        self.assertEqual(date_end.hour, 23)
        self.assertEqual(date_end.minute, 59)
        self.assertEqual(date_end.second, 59)

    def test_10_days_custom1(self):
        print "----------------10 days custom-1 ---------------"
        date = datetime(2016, 8, 12)
        date_reference = datetime(2016, 7, 15)
        tf = self._get_tf(10, self.DAYS)
        date_start, date_end = tf.get_start_end_dates(date, date_reference)
        print "Date start [%s]" % date_start
        print "Date end [%s]" % date_end
        self.assertEqual(date_start.year, 2016)
        self.assertEqual(date_start.month, 8)
        self.assertEqual(date_start.day, 5)
        self.assertEqual(date_start.hour, 0)
        self.assertEqual(date_start.minute, 0)
        self.assertEqual(date_start.second, 0)

        self.assertEqual(date_end.year, 2016)
        self.assertEqual(date_end.month, 8)
        self.assertEqual(date_end.day, 14)
        self.assertEqual(date_end.hour, 23)
        self.assertEqual(date_end.minute, 59)
        self.assertEqual(date_end.second, 59)

    def test_10_days_custom2(self):
        print "----------------10 days custom-2 ---------------"
        date = datetime(2016, 7, 7)
        date_reference = datetime(2016, 7, 15)
        tf = self._get_tf(10, self.DAYS)
        date_start, date_end = tf.get_start_end_dates(date, date_reference)
        print "Date start [%s]" % date_start
        print "Date end [%s]" % date_end
        self.assertEqual(date_start.year, 2016)
        self.assertEqual(date_start.month, 07)
        self.assertEqual(date_start.day, 6)
        self.assertEqual(date_start.hour, 0)
        self.assertEqual(date_start.minute, 0)
        self.assertEqual(date_start.second, 0)

        self.assertEqual(date_end.year, 2016)
        self.assertEqual(date_end.month, 07)
        self.assertEqual(date_end.day, 15)
        self.assertEqual(date_end.hour, 23)
        self.assertEqual(date_end.minute, 59)
        self.assertEqual(date_end.second, 59)

    def test_2_weeks_custom1(self):
        print "----------------2 weeks custom-1 ---------------"
        date = datetime(2016, 8, 12)
        date_reference = datetime(2016, 7, 15)
        tf = self._get_tf(2, self.WEEKS)
        date_start, date_end = tf.get_start_end_dates(date, date_reference)
        print "Date start [%s]" % date_start
        print "Date end [%s]" % date_end
        self.assertEqual(date_start.year, 2016)
        self.assertEqual(date_start.month, 7)
        self.assertEqual(date_start.day, 30)
        self.assertEqual(date_start.hour, 0)
        self.assertEqual(date_start.minute, 0)
        self.assertEqual(date_start.second, 0)

        self.assertEqual(date_end.year, 2016)
        self.assertEqual(date_end.month, 8)
        self.assertEqual(date_end.day, 12)
        self.assertEqual(date_end.hour, 23)
        self.assertEqual(date_end.minute, 59)
        self.assertEqual(date_end.second, 59)

    def test_2_weeks_custom2(self):
        print "----------------2 weeks custom-2 ---------------"
        date = datetime(2016, 7, 7)
        date_reference = datetime(2016, 7, 15)
        tf = self._get_tf(2, self.WEEKS)
        date_start, date_end = tf.get_start_end_dates(date, date_reference)
        print "Date start [%s]" % date_start
        print "Date end [%s]" % date_end
        self.assertEqual(date_start.year, 2016)
        self.assertEqual(date_start.month, 07)
        self.assertEqual(date_start.day, 2)
        self.assertEqual(date_start.hour, 0)
        self.assertEqual(date_start.minute, 0)
        self.assertEqual(date_start.second, 0)

        self.assertEqual(date_end.year, 2016)
        self.assertEqual(date_end.month, 07)
        self.assertEqual(date_end.day, 15)
        self.assertEqual(date_end.hour, 23)
        self.assertEqual(date_end.minute, 59)
        self.assertEqual(date_end.second, 59)

    def test_2_years_custom1(self):
        print "----------------2 years custom-1 ---------------"
        date = datetime(2016, 8, 12)
        date_reference = datetime(2016, 7, 15)
        tf = self._get_tf(2, self.YEARS)
        date_start, date_end = tf.get_start_end_dates(date, date_reference)
        print "Date start [%s]" % date_start
        print "Date end [%s]" % date_end
        self.assertEqual(date_start.year, 2016)
        self.assertEqual(date_start.month, 7)
        self.assertEqual(date_start.day, 15)

        self.assertEqual(date_end.year, 2018)
        self.assertEqual(date_end.month, 7)
        self.assertEqual(date_end.day, 15)

    def test_2_years_custom2(self):
        print "----------------2 years custom-2 ---------------"
        date = datetime(2016, 7, 7)
        date_reference = datetime(2016, 7, 15)
        tf = self._get_tf(2, self.YEARS)
        date_start, date_end = tf.get_start_end_dates(date, date_reference)
        print "Date start [%s]" % date_start
        print "Date end [%s]" % date_end
        self.assertEqual(date_start.year, 2014)
        self.assertEqual(date_start.month, 7)
        self.assertEqual(date_start.day, 16)

        self.assertEqual(date_end.year, 2016)
        self.assertEqual(date_end.month, 7)
        self.assertEqual(date_end.day, 14)

    def _get_tf(self, nb, type):
        tf = self.env['procurement.time.frame'].create({
            'name': "%s %s" % (nb, type),
            'nb': nb,
            'today_as_ref': True,
            'period_type': type
        })
        return tf
