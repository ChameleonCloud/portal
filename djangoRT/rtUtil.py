import rt
from django.conf import settings
from datetime import datetime

class DjangoRt:

	CLOSED = 'closed'
	RESOLVED = 'resolved'
	OPEN = 'open'
	NEW = 'new'
	RESPONSE_REQUIRED = 'response required'

	def __init__(self):
		self.rtHost = settings.DJANGO_RT['RT_HOST']
		self.rtUn = settings.DJANGO_RT['RT_UN']
		self.rtPw = settings.DJANGO_RT['RT_PW']
		self.rtQueue = settings.DJANGO_RT['RT_QUEUE']
		# self.defaultEmail = DEFAULT_EMAIL

		self.tracker = rt.Rt(self.rtHost, self.rtUn, self.rtPw, basic_auth=(self.rtUn, self.rtPw))
		self.tracker.login()

	def getUserTickets(self, userEmail, status="ALL"):
		# if not userEmail and self.defaultEmail:
		# 	userEmail = self.defaultEmail
		if not status == "ALL":
			ticket_list = self.tracker.search(Queue=rt.ALL_QUEUES, Requestors__exact=userEmail, Status__exact=status, order='-LastUpdated')
		else:
			ticket_list = self.tracker.search(Queue=rt.ALL_QUEUES, Requestors__exact=userEmail, order='-LastUpdated')

		for ticket in ticket_list:
			ticket['id'] = ticket['id'].replace('ticket/', '')
			ticket['LastUpdated'] = datetime.strptime(ticket['LastUpdated'], '%a %b %d %X %Y')

		return ticket_list

	def getTicket(self, ticket_id):
		ticket = self.tracker.get_ticket(ticket_id)

		ticket['id'] = ticket['id'].replace('ticket/', '')

		return ticket

	def getTicketHistory(self, ticket_id):
		ticketHistory = self.tracker.get_history(ticket_id)

		for ticket in ticketHistory:
			ticket['Created'] = datetime.strptime(ticket['Created'], '%Y-%m-%d %X')

		return ticketHistory

	# Returns the ticket id of the created ticket
	def createTicket(self, ticket):
		return self.tracker.create_ticket(Queue=self.rtQueue,
				Subject=ticket.subject,
				Text=ticket.problem_description,
				Requestors=ticket.requestor,
				Cc=",".join(ticket.cc))

	def replyToTicket(self, ticket_id, reply_text):
		return self.tracker.reply(ticket_id, text=reply_text)

	# Checks if the current user is a requestor or CC on the ticket
	# Also doesn't crap out if the user isn't logged in even though
	# we should be checking before calling this
	def hasAccess(self, ticket_id, user = None):
		# TODO remove once emails are being set
		# if not user and self.defaultEmail:
		# 	user = self.defaultEmail
		if user and ticket_id:
			ticket = self.tracker.get_ticket(ticket_id)
			if user in ticket.get('Requestors', '') or user in ticket.get('Cc', ''):
				return True

		return False
