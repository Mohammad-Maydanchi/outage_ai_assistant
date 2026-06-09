/**
 * Hard IVR stress test — AT&T-style BRANCHING phone menu (Twilio Function).
 *
 * Tests that the agent doesn't get stuck:
 *  - deep navigation: main -> technical support (3) -> internet (2) -> report outage (2)
 *  - decoy / wrong-turn recovery: a wrong key says "not available" and returns to main
 *  - retry on no input: a menu with no keypress repeats itself
 *  - keypad data entry: "enter your 10-digit phone number followed by #"
 *  - then the outage result (severe weather, 9 PM, ref 67890)
 *
 * SETUP: create a Twilio Function at path "/ivr", paste this code, Deploy,
 * then point the phone number's "A call comes in" webhook to the function URL.
 * (The code self-references "/ivr", so the function path MUST be /ivr.)
 */
exports.handler = function (context, event, callback) {
  const twiml = new Twilio.twiml.VoiceResponse();
  const V = { voice: 'Polly.Joanna' };
  const step = event.step || 'main';
  const digit = (event.Digits || '').trim();
  const url = (s) => `https://${context.DOMAIN_NAME}/ivr?step=${s}`;

  // Present a menu; if no key is pressed, repeat the same menu.
  const ask = (sameStep, prompt, opts) => {
    const g = twiml.gather(Object.assign({ numDigits: 1, timeout: 8, action: url(sameStep) }, opts || {}));
    g.say(V, prompt);
    twiml.redirect(url(sameStep));
  };
  const wrong = () => {
    twiml.say(V, "Sorry, that option isn't available. Let's start over.");
    twiml.redirect(url('main'));
  };

  switch (step) {
    case 'main':
      if (digit === '3') twiml.redirect(url('support'));
      else if (digit && digit !== '9') wrong();
      else ask('main', 'Thank you for calling A T and T. For new service, press 1. For billing, press 2. For technical support, press 3. For account changes, press 4. To repeat this menu, press 9.');
      break;
    case 'support':
      if (digit === '2') twiml.redirect(url('internet'));
      else if (digit) wrong();
      else ask('support', 'Technical support. For TV service, press 1. For internet, press 2. For phone service, press 3.');
      break;
    case 'internet':
      if (digit === '2') twiml.redirect(url('verify'));
      else if (digit) wrong();
      else ask('internet', 'Internet support. For slow speeds, press 1. To report an outage, press 2. For equipment help, press 3.');
      break;
    case 'verify':
      if (digit) twiml.redirect(url('result'));
      else ask('verify', 'To look up your account, enter your ten digit phone number, followed by the pound key.', { finishOnKey: '#', numDigits: 15, timeout: 12 });
      break;
    case 'result':
      twiml.say(V, 'Thank you. One moment while I check our systems.');
      twiml.pause({ length: 2 });
      twiml.say(V, 'Yes, A T and T is aware of an internet outage in your area, caused by severe weather. The estimated restoration time is 9 P M tonight. Your reference number is 6 7 8 9 0. Goodbye.');
      twiml.hangup();
      break;
    default:
      twiml.redirect(url('main'));
  }

  callback(null, twiml);
};
