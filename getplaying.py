from sxm import SiriusXM
from secrests import secrets

s = SiriusXM(secrets['username'], secrets['password'])
print (s.get_playlist('Octane'))
