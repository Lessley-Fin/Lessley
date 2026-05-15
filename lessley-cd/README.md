### How to insert init mongo using .json files:
# Insert into mongodb container
```bash
docker cp ..\lessley-backend\Lessley.Personalization\resources\stores.json e617a141c059:/tmp/store_list.json                                                                         
```
# Read from container and write to mongodb 
```bash
docker exec -it e617a141c059 mongoimport --db lessley --collection store_list --file /tmp/store_list.json --jsonArray --username guest --password guest --authenticationDatabase admin
```

# Steps:
# 1:
```bash
docker ps
```

```bash
CONTAINER ID   IMAGE                         COMMAND                  CREATED          STATUS                    PORTS                                                                                          NAMES
d880d2dec8b7   mongo-express:latest          "/sbin/tini -- /dock…"   14 minutes ago   Up 14 minutes             0.0.0.0:8081->8081/tcp, [::]:8081->8081/tcp                                                    mongo_express


```
# 2:
# 3:
# 4:
# 5:
# 6