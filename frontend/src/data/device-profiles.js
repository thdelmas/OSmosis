import computer from './devices-computer.json'
import console from './devices-console.json'
import iot from './devices-iot.json'
import phoneBq from './devices-phone-bq.json'
import phoneGoogle from './devices-phone-google.json'
import phoneNothing from './devices-phone-nothing.json'
import phonePine64 from './devices-phone-pine64.json'
import phonePurism from './devices-phone-purism.json'
import phoneSamsung from './devices-phone-samsung.json'
import sbc from './devices-sbc.json'
import tablet from './devices-tablet.json'

export default [
  ...computer,
  ...console,
  ...iot,
  ...phoneBq,
  ...phoneGoogle,
  ...phoneNothing,
  ...phonePine64,
  ...phonePurism,
  ...phoneSamsung,
  ...sbc,
  ...tablet,
]
