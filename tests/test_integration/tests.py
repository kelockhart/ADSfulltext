import unittest
import time
import json
from pipeline import psettings
from pipeline.workers import RabbitMQWorker, CheckIfExtractWorker, StandardFileExtractWorker
from pipeline.ADSfulltext import TaskMaster
from run import publish, read_links_from_file


class TestExtractWorker(unittest.TestCase):

    def setUp(self):
        # Load the extraction worker
        check_params = psettings.WORKERS['CheckIfExtractWorker']
        standard_params = psettings.WORKERS['StandardFileExtractWorker']

        for params in [check_params, standard_params]:
            params['RABBITMQ_URL'] = psettings.RABBITMQ_URL
            params['extract_key'] = "FULLTEXT_EXTRACT_PATH_UNITTEST"
            params['TEST_RUN'] = True

        self.check_worker = CheckIfExtractWorker(params=check_params)
        self.standard_worker = StandardFileExtractWorker(params=standard_params)
        self.standard_worker.logger.debug("params: %s" % standard_params)

    def test_extraction_of_non_extracted(self):

        # user loads the list of full text files
        test_publish = 'tests/test_integration/stub_data/fulltext.links'
        records = read_links_from_file(test_publish)
        self.assertEqual(len(records.bibcode), 5)

        # Converts the input into a user defined payload
        records.make_payload()
        self.assertTrue(len(records.payload)>0)

        # Queues and routes are started
        TM = TaskMaster(psettings.RABBITMQ_URL, psettings.RABBITMQ_ROUTES, psettings.WORKERS)
        TM.initialize_rabbitmq()

        # The worker connects to the queue
        publish_worker = RabbitMQWorker()
        ret_queue = publish_worker.connect(psettings.RABBITMQ_URL)
        self.assertTrue(ret_queue)

        # External worker publishes to the rabbitmq queue
        ret = publish(publish_worker, records.payload, exchange='FulltextExtractionExchange',
                      routing_key='CheckIfExtractRoute')
        self.assertTrue(ret)
        time.sleep(10)

        # Worker receives packet of information and checks to see if it needs to be updated
        # time.sleep(5) do not use time.sleep,
        # see: http://stackoverflow.com/questions/22061082/\
        # getting-pika-exceptions-connectionclosed-error-while-using-rabbitmq-in-python

        self.check_worker.run()
        time.sleep(10)

        # Check to see if the correct number of updates got published to the next queue
        # Re-declare the queue with passive flag
        standard_queue = self.check_worker.channel.queue_declare(
            queue="StandardFileExtractorQueue",
            passive=True
            )

        pdf_queue = self.check_worker.channel.queue_declare(
            queue="PDFFileExtractorQueue",
            passive=True
            )

        # results = json.loads(self.check_worker.results)
        # self.assertIn('STALE_CONTENT', results, "Result was different to what was expected: %s" % results)

        pdf_expected = [{"bibcode": "test", "ft_source": "/vagrant/tests/test_unit/stub_data/te/st/test.pdf", "provider": "MNRAS", \
                                "UPDATE": "STALE_CONTENT"},
                            {"bibcode": "test", "ft_source": "tests/test_unit/stub_data/te/st/test.pdf", "provider": "MNRAS", \
                                "UPDATE": "DIFFERING_FULL_TEXT"},
                            {"bibcode": "test3", "ft_source": "/vagrant/tests/test_unit/stub_data/te/st/test.pdf", "provider": "MNRAS", \
                                "UPDATE": "MISSING_FULL_TEXT"},
                            ]

        standard_expected = [{"bibcode": "test1", "ft_source": "tests/test_unit/stub_data/te/st/test.ocr", "provider": "MNRAS", \
                                "UPDATE": "NOT_EXTRACTED_BEFORE"},
                            ]

        pdf_res, standard_res = json.loads(self.check_worker.results["PDF"]), json.loads(self.check_worker.results["Standard"])

        self.assertEqual(pdf_res, pdf_expected)
        self.assertEqual(standard_res, standard_expected)
        # self.assertEqual(self.check_worker.results, 'pass')
        self.assertTrue(pdf_queue.method.message_count == 1,
                        "PDF queue should have 1 message, but it has: %d" % pdf_queue.method.message_count)

        # Clean-up for next test: should be removed when next queue implemented
        # self.check_worker.channel.queue_purge(queue="StandardFileExtractorQueue")
        self.check_worker.channel.queue_purge(queue="PDFFileExtractorQueue")

        # There should be no errors at this stage
        queue_error = self.check_worker.channel.queue_declare(
            queue="ErrorHandlerQueue",
            passive=True
            )
        self.assertTrue(queue_error.method.message_count == 0,
                        "Should be 0, but it is: %d" % queue_error.method.message_count)

        # Standard Extractor should extract the content of the given payload
        self.standard_worker.run()
        standard_res = json.loads(self.standard_worker.results)
        standard_expected = [{"bibcode": "test1", "ft_source": "tests/test_unit/stub_data/te/st/test.ocr", "provider": "MNRAS", \
                                "UPDATE": "NOT_EXTRACTED_BEFORE", "full_text": "FULL TEXT", "meta_path": ""},
                            ]

        self.assertEqual(standard_res, standard_expected)

        # When extracted, the payload should no longer exist within the standard file queue
        # self.assertTrue(standard_queue.method.message_count == 0,
        #                 "Standard queue should have 1 message, but it has: %d" % standard_queue.method.message_count)

        # The content is extracted and passed on as a payload, it now must be written to file

        # ErrorHandler should go through any of the problems that arose and deal with them


if __name__ == "__main__":
    unittest.main()