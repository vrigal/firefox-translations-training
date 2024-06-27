for i in `cat /tmp/links`; do curl https://firefoxci.taskcluster-artifacts.net/$i/0/public/logs/live_backing.log > ~/Downloads/$i.log; done

for i in `cat /tmp/links`; do WANDB_PUBLICATION=true TASKCLUSTER_PROXY_URL=https://firefox-ci-tc.services.mozilla.com TASK_ID=$i ./pipeline/eval/eval.py --taskcluster-secret=1; done
