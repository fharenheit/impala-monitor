import os
from unittest import TestCase
from datetime import datetime
from impala_monitor.logger.parser import ImpalaQueryLogParser
from impala_monitor.logger.parser import Query
from impala_monitor.logger.parser import Converter


class HtmlLoader(object):
    def __init__(self):
        self.base_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            'fixtures'
        )

    def load(self, file_name: str) -> str:
        full_path = os.path.join(
            self.base_path, file_name
        )

        with open(full_path, 'r') as buffer:
            html = buffer.read()
        buffer.close()

        return html


class ConverterTest(TestCase):
    def test_convert_from_gb_to_mb(self):
        value = Converter.convert('2.03GB', 'MB')

        self.assertEqual(value, 2030)

    def test_convert_from_mb_to_gb(self):
        value = Converter.convert('323MB', 'GB')

        self.assertEqual(0.323, value)

    def test_convert_same_unit(self):
        value = Converter.convert('2.34GB', 'GB')

        self.assertEqual(value, 2.34)


class ImpalaQueryLogParserTest(TestCase):
    def test_extract_query_id(self):
        query_id = ImpalaQueryLogParser.extract_query_id(
            '/query_profile?query_id=dasdsa8798das8798das:dsa'
        )

        self.assertEqual(query_id, 'dasdsa8798das8798das:dsa')

    def test_get_queries(self):
        html = HtmlLoader().load('impala_queries.html')
        parser = ImpalaQueryLogParser(html)

        queries = parser.queries

        self.assertEqual(20, len(queries))

        for query in queries:
            self.assertIsInstance(query, Query)
            self.assertIsInstance(query.start_time, datetime)
            self.assertIsInstance(query.end_time, datetime)

    def test_extract_profile_data(self):
        html = HtmlLoader().load('impala_query_profile.html')
        parser = ImpalaQueryLogParser(html)

        query = Query({'query_id': '1234', 'query': 'aaa'})

        query = parser.extract_profile(query)

        self.assertEqual('2.13GB', query.memory_allocated)
        self.assertEqual('2', query.vcores_allocated)
        self.assertEqual('1234', query.query_id)
