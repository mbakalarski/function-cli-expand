# Example manifests

You can run your function locally and test it using `crossplane render`
with these example manifests.

```shell
# Run the function locally
hatch run development
```

```shell
# Then, in another terminal, call it with these example manifests

AVD_COMMIT=a5d01648e468a6637b41f5078d7d1c45985a796c
AVD_DESIGN=single-dc-l3ls
DEVICE_HOSTNAME=dc1-spine1

URL="https://raw.githubusercontent.com/aristanetworks/avd/${AVD_COMMIT}/ansible_collections/arista/avd/examples/${AVD_DESIGN}/intended/configs/${DEVICE_HOSTNAME}.cfg"

crossplane render \
  <(kubectl create configmap ${DEVICE_HOSTNAME}-cfg --from-file=${DEVICE_HOSTNAME}.cfg=<(curl -sf "$URL") --dry-run=client -o yaml) \
  composition.yaml \
  functions.yaml \
  --required-resources secret.yaml \
  --extra-resources environment.yaml \
  -r
```
