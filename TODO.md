# TODO

## Functionality

- [ ] add registration key to config
- [ ] add registration logic as part of configuration flow
  - removes requirement for device to have been paired. instead need to put device in pairing mode
- [ ] detect version based on sw & hw version info
- [ ] add delayed start?

## Polish

- [ ] improve test coverage, especially for the HA component
- [ ] handle failure to handshake with status=1 as -> reg required
- [ ] handle failure to register with status=1 as -> device not in pairing mode
- [ ] add error states

## Docs:

- [ ] note: device will not be found if actively connected already (e.g. to app or other integration)
- [ ] simplify docs. remove irrelevant stuff
